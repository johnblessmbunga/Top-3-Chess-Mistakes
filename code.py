import chess
import chess.engine
import chess.pgn
import io
import pygame
import sys
import os
import pyperclip
import re

#Stockfish Path
STOCKFISH_PATH = "C:/Users/johnb/Documents/Apps/stockfish/stockfish-windows-x86-64-avx2.exe"

# Board and piece image settings
os.environ['SDL_VIDEO_CENTERED'] = '1' #Centre all window screens
SQUARE_SIZE = 60
BOARD_SIZE = SQUARE_SIZE * 8
EXTRA_HEIGHT = 60  # Space above and below the board for instructions/info
SIDE_PANEL_WIDTH = BOARD_SIZE  # 100% extension
WINDOW_WIDTH = BOARD_SIZE + SIDE_PANEL_WIDTH
WINDOW_HEIGHT = BOARD_SIZE + 2 * EXTRA_HEIGHT
PIECE_IMAGES = {}

def load_piece_images():
    pieces = ['r', 'n', 'b', 'q', 'k', 'p']
    colors = ['w', 'b']
    for color in colors:
        for piece in pieces:
            img = pygame.image.load(f"assets/{color}{piece}.png")
            PIECE_IMAGES[color + piece] = pygame.transform.scale(img, (SQUARE_SIZE, SQUARE_SIZE))

def draw_board(screen, board, player_color="white"):
    """
    Draws the chess board with the given orientation.
    player_color: "white" (default, white at bottom) or "black" (black at bottom)
    """
    # Set colors so that light is always at bottom right for both orientations
    colors = [pygame.Color(181, 136, 99), pygame.Color(240, 217, 181)]  # dark, light

    for rank in range(8):
        for file in range(8):
            # Flip the board if black is at the bottom
            display_rank = rank if player_color == "white" else 7 - rank
            display_file = file if player_color == "white" else 7 - file
            color = colors[(display_rank + display_file) % 2]
            pygame.draw.rect(
                screen,
                color,
                pygame.Rect(file * SQUARE_SIZE, (7 - rank) * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
            )
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            color = 'w' if piece.color == chess.WHITE else 'b'
            img = PIECE_IMAGES[color + piece.symbol().lower()]
            file = chess.square_file(square)
            rank = chess.square_rank(square)
            # Flip the board if black is at the bottom
            display_file = file if player_color == "white" else 7 - file
            display_rank = rank if player_color == "white" else 7 - rank
            screen.blit(img, (display_file * SQUARE_SIZE, (7 - display_rank) * SQUARE_SIZE))

def evaluate_fen(fen, engine, turn):
    board = chess.Board(fen)
    info = engine.analyse(board, chess.engine.Limit(time=0.1))
    score = info["score"]
    # Use .white() or .black() based on whose turn it is
    if turn == chess.WHITE:
        s = score.white()
    else:
        s = score.black()
    if s.is_mate():
        return f"# {s.mate()}"
    return s.score() / 100
def is_endgame(board):
    """
    Returns "yes" if both sides have 2 or fewer minor/major pieces (not counting pawns/kings), else "no".
    """
    minor_major = [chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT]
    white_material = sum(len(board.pieces(pt, chess.WHITE)) for pt in minor_major)
    black_material = sum(len(board.pieces(pt, chess.BLACK)) for pt in minor_major)
    return "yes" if (white_material <= 2 and black_material <= 2) else "no"


def get_player_color(pgn_string, username):
    """
    Returns 'white' or 'black' depending on which color the username played in the PGN.
    If username not found, returns None.
    """
    game = chess.pgn.read_game(io.StringIO(pgn_string))
    white = game.headers.get("White", "").strip().lower()
    black = game.headers.get("Black", "").strip().lower()
    username_lower = username.strip().lower()
    if username_lower == white:
        return "white"
    elif username_lower == black:
        return "black"
    else:
        return None

def pgn_parser(pgn_string):
    # First, check PGN structure before move legality
    structure_valid, structure_message = is_pgn_structurally_valid(pgn_string)
    if not structure_valid:
        return False, structure_message
    # Remove header lines and join move text
    lines = pgn_string.strip().split('\n')
    move_lines = [line for line in lines if not line.startswith('[')]
    move_text = ' '.join(move_lines)
    # Remove result (e.g. 1-0, 0-1, 1/2-1/2)
    move_text = re.sub(r"\d-\d|\d/\d-\d/\d", "", move_text)
    # Remove comments and NAGs
    move_text = re.sub(r"\{[^}]*\}", "", move_text)
    move_text = re.sub(r"\$\d+", "", move_text)
    # Split into tokens
    tokens = move_text.split()
    # Remove move numbers
    moves = [tok for tok in tokens if not re.match(r"^\d+\.*$", tok)]
    board = chess.Board()
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()
    try:
        for idx, san in enumerate(moves):
            found_move = None
            for move in board.legal_moves:
                try:
                    if board.san(move) == san:
                        found_move = move
                        break
                except Exception:
                    continue
            if found_move:
                board.push(found_move)
            else:
                move_number = board.fullmove_number
                side = "White" if board.turn == chess.WHITE else "Black"
                move_prefix = f"{move_number}." if board.turn == chess.WHITE else f"{move_number}..."
                return False, f"Illegal move {move_prefix} {san} ({side})"
        return True, None
    finally:
        sys.stderr = old_stderr  # Always restore stderr after all parsing
def is_pgn_structurally_valid(pgn_string):
    """
    Checks if the PGN string has a valid structure:
    - Contains at least required headers ([Event], [Site], [Date], [White], [Black])
    - Headers are in correct format ([Key "Value"])
    - Contains at least one move in valid SAN notation
    - Does not look like plain text or random input
    Returns (True, None) if valid, (False, error_message) if not.
    """

    # 1. Check for required headers and malformed headers
    required_headers = ["Event", "Site", "Date", "White", "Black"]
    headers_found = {h: False for h in required_headers}
    header_pattern = re.compile(r'^\[(\w+)\s+"(.*)"\]$')
    lines = pgn_string.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Simple error message for header issues
        #if not line.startswith('[')  and any(h in line for h in required_headers):
            #return False, f"PGN Header Error: Missing opening bracket in header: {line}"
        # Check for unclosed bracket or quote in header lines
        if line.startswith('['):
            if not line.endswith(']'):
                return False, "PGN Structure Error"
            if line.count('"') % 2 != 0:
                return False, "PGN Structure Error"
            m = header_pattern.match(line)
            if m:
                key = m.group(1)
                if key in headers_found:
                    headers_found[key] = True
        elif line and not line.startswith('['):
            break  # Stop checking headers once moves start

    missing = [h for h, found in headers_found.items() if not found]
    if missing:
        return False, "PGN Structure Error"

    # 2. Check for at least one move in SAN notation
    move_lines = [line for line in lines if not line.startswith('[') and line.strip()]
    move_text = ' '.join(move_lines)
    # Remove result
    move_text = re.sub(r"\d-\d|\d/\d-\d/\d", "", move_text)
    # Remove comments and NAGs
    move_text = re.sub(r"\{[^}]*\}", "", move_text)
    move_text = re.sub(r"\$\d+", "", move_text)
    # Split into tokens
    tokens = move_text.split()
    # Remove move numbers
    moves = [tok for tok in tokens if not re.match(r"^\d+\.*$", tok)]
    # Remove result tokens
    moves = [tok for tok in moves if tok not in ["1-0", "0-1", "1/2-1/2", "*"]]

    # Basic SAN move pattern: e4, Nf3, Qxe5, O-O, O-O-O, etc.
    san_pattern = re.compile(r"^(O-O(-O)?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](=[QRBN])?|[a-h][1-8])[\+#=]?$")
    valid_moves = [m for m in moves if san_pattern.match(m)]
    if not valid_moves:
        return False, "PGN Structure Error"

    # 3. Check for plain text (e.g., "hello world" or random text)
    if len(valid_moves) < max(1, len(moves) // 2):
        return False, "PGN Structure Error"

    return True, None
def find_mistakes(pgn_string, color,stockfish_path):
    """
    Returns a dictionary of mistakes for the given color.
    The dictionary has keys: 'all', 'opening', 'middlegame', 'endgame'.
    Each value is a list of tuples: (move_number, move, evaluation, change_in_eval)
    A mistake is any move that reduces evaluation by 0.2 or more,
    but NOT if the move is the engine's best move.
    The lists are sorted by the largest negative change in evaluation (worst mistakes first).
    """
    game = chess.pgn.read_game(io.StringIO(pgn_string))
    board = game.board()
    mistakes = {
        "all": [],
        "opening": [],
        "middlegame": [],
        "endgame": []
    }
    prev_eval = 0
    color = color.lower()
    total_penalty=0
    move_number = 0
    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
        for move in game.mainline_moves():
            move_number = board.fullmove_number
            side = "white" if board.turn else "black"
            move_san = board.san(move)
            #Get the best move from the engine for this position
            info = engine.analyse(board, chess.engine.Limit(time=0.5))
            best_move = info.get("pv", [None])[0]
            #Only record as mistake if move is NOT the best move
            if best_move is not None and move == best_move:
                board.push(move)
                try:
                    prev_eval = float(evaluate_fen(board.fen(), engine, chess.WHITE if color == "white" else chess.BLACK))
                except Exception:
                    prev_eval = 0
                continue
            is_endgame_phase = is_endgame(board)
            board.push(move)
            #Always evaluate from the specified color's perspective
            eval_turn = chess.WHITE if color == "white" else chess.BLACK
            eval_score = evaluate_fen(board.fen(), engine, eval_turn)
            if side == color:
                try:
                    eval_float = float(eval_score)
                    prev_float = float(prev_eval)
                    change = eval_float - prev_float
                    
                    if change < -0.2:
                        #mistake found and recorded
                        total_penalty += abs(max(change,-1))
                        mistakes["all"].append((move_number, move_san, eval_score, change))
                        #mistake based on game stage
                        if move_number <= 10:
                            mistakes["opening"].append((move_number, move_san, eval_score, change))
                        elif is_endgame_phase == "yes":
                            mistakes["endgame"].append((move_number, move_san, eval_score, change))
                        else:
                            mistakes["middlegame"].append((move_number, move_san, eval_score, change))
                except Exception:
                    pass  # skip mate scores or errors
            try:
                prev_eval = float(eval_score)
            except Exception:
                prev_eval = 0
    # Sort each list by the largest negative change (worst first)
    for key in mistakes:
        mistakes[key].sort(key=lambda x: x[3])
        mistakes[key] = mistakes[key][:3]  # Keep only the top 3 mistakes
    if move_number!=0:
        accuracy = max(0.0, 1 - (total_penalty / move_number))
    else:
        accuracy = 1.0
    return mistakes, accuracy
def start_window(username, stockfish_path):
    """
    Displays a Pygame window with a title and a text box for the user to paste or type a PGN string.
    Returns the entered PGN string when the user presses Enter.
    Supports vertical scrolling if the text exceeds the input box height.
    """
    pygame.init()
    menu_width, menu_height = 700, 350
    screen = pygame.display.set_mode((menu_width, menu_height))
    pygame.display.set_caption("Enter PGN")
    title_font = pygame.font.SysFont(None, 44)
    font = pygame.font.SysFont(None, 32)
    input_font = pygame.font.SysFont(None, 28)

    input_box = pygame.Rect(40, 120, menu_width - 80, 120)
    color_inactive = pygame.Color('lightskyblue3')
    color_active = pygame.Color('dodgerblue2')
    color = color_inactive
    active = False
    text = ""
    done = False

    instructions = "Paste or type your PGN below, then press Enter to continue."

    # Scrolling variables
    scroll_offset = 0
    horiz_scroll_offset = 0
    line_height = 30
    max_visible_lines = input_box.height // line_height
    max_visible_chars = (input_box.width - 10) // input_font.size(" ")[0]

    # Enter button
    enter_button_width = 120
    enter_button_height = 40
    enter_button_x = (menu_width - enter_button_width) // 2
    enter_button_y = input_box.bottom + 30
    enter_button_rect = pygame.Rect(enter_button_x, enter_button_y, enter_button_width, enter_button_height)
    enter_button_font = pygame.font.SysFont(None, 28)
    enter_button_text = enter_button_font.render("Enter", True, (255, 255, 255))
    def handle_pgn_entry(text, username, stockfish_path, screen, menu_width, menu_height):
        """
        Helper function for Enter button and Enter key in start_window.
        Handles PGN validation, color detection, mistake finding, and error display.
        """
        if not text.strip():
            error_font = pygame.font.SysFont(None, 32)
            error_message = "No PGN Entered"
            error_surface = error_font.render(error_message, True, (255, 80, 80))
            screen.blit(error_surface, ((menu_width - error_surface.get_width()) // 2, menu_height // 2 + 40))
            pygame.display.flip()
            pygame.time.wait(2000)
            start_window(username, stockfish_path)
            return
    
        # Show loading screen while generating mistakes
        loading = True
        error_message = None
        while loading:
            screen.fill((40, 40, 40))
            loading_font = pygame.font.SysFont(None, 44)
            loading_text = loading_font.render("Analyzing game, please wait...", True, (220, 220, 220))
            screen.blit(loading_text, ((menu_width - loading_text.get_width()) // 2, menu_height // 2 - 22))
            pygame.display.flip()
            try:
                is_valid, message = pgn_parser(text)
                if not is_valid:
                    error_message = message
                    loading = False
                else:
                    color = get_player_color(text, username)
                    if color is None:
                        error_message = f"Username '{username}' not found in PGN."
                        loading = False
                    else:
                        mistakes, accuracy = find_mistakes(text, color, stockfish_path)
                        loading = False
                        mainmenu(text, color, stockfish_path, mistakes, accuracy)
            except Exception:
                error_message = "Invalid PGN entered. Please check your input."
                loading = False
        if error_message:
            error_font = pygame.font.SysFont(None, 32)
            error_surface = error_font.render(error_message, True, (255, 80, 80))
            screen.blit(error_surface, ((menu_width - error_surface.get_width()) // 2, menu_height // 2 - 45))
            pygame.display.flip()
            pygame.time.wait(2000)
            start_window(username, stockfish_path)

    error_message = None


    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                else:
                    active = False
                color = color_active if active else color_inactive
                # Vertical scrollbar click
                if (input_box.right <= event.pos[0] <= input_box.right + 15 and
                    input_box.top <= event.pos[1] <= input_box.bottom):
                    # Calculate line based on click position
                    lines = text.split('\n')
                    total_lines = len(lines)
                    if total_lines > max_visible_lines:
                        rel_y = event.pos[1] - input_box.top
                        scroll_offset = int((rel_y / input_box.height) * (total_lines - max_visible_lines))
                # Horizontal scrollbar click
                if (input_box.left <= event.pos[0] <= input_box.right and
                    input_box.bottom + 3 <= event.pos[1] <= input_box.bottom + 13):
                    if max_line_pixel_width > input_box_inner_width:
                        rel_x = event.pos[0] - input_box.left
                        max_offset = max_line_pixel_width - input_box_inner_width
                        horiz_scroll_offset = int((rel_x / input_box.width) * max_offset)
                # Enter button click
                if enter_button_rect.collidepoint(event.pos):
                    done = True
                    handle_pgn_entry(text, username, stockfish_path, screen, menu_width, menu_height)#PGN Entered
            elif event.type == pygame.KEYDOWN:
                if active:
                    # Handle Ctrl+V for paste
                    if (event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL)):
                        try:
                            clip_text = pyperclip.paste()
                            if clip_text:
                                text += clip_text
                        except Exception:
                            pass
                    elif event.key == pygame.K_RETURN:
                        done = True
                        handle_pgn_entry(text, username, stockfish_path, screen, menu_width, menu_height)#PGN Entered
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]#delete text
                    elif event.key == pygame.K_UP:
                        scroll_offset = max(0, scroll_offset - 1)#scroll up
                    elif event.key == pygame.K_DOWN:
                        lines = text.split('\n')#scro;; down
                        total_lines = len(lines)
                        scroll_offset = min(max(0, total_lines - max_visible_lines), scroll_offset + 1)
                    elif event.key == pygame.K_LEFT:
                        horiz_scroll_offset = max(0, horiz_scroll_offset - 20)#scroll left
                    elif event.key == pygame.K_RIGHT:
                        max_offset = max_line_pixel_width - input_box_inner_width
                        horiz_scroll_offset = min(max(0, max_offset), horiz_scroll_offset + 20)  # scroll right
                    else:
                        if event.unicode.isprintable():
                            text += event.unicode
        if done:#window no longer active
            break
        screen.fill((40, 40, 40))#build window
        title = title_font.render("Top 3 Chess Mistakes", True, (220, 220, 220))
        screen.blit(title, ((menu_width - title.get_width()) // 2, 30))
        instr = font.render(instructions, True, (200, 200, 200))
        screen.blit(instr, ((menu_width - instr.get_width()) // 2, 80))

        # Draw input box
        pygame.draw.rect(screen, color, input_box, 3)

        # Render the current text (multi-line support with vertical and horizontal scrolling)
        lines = text.split('\n')
        total_lines = len(lines)
        visible_lines = lines[scroll_offset:scroll_offset + max_visible_lines]
        # Use the longest line in ALL lines for horizontal scroll
        max_line_len = max((len(line) for line in lines), default=0)
        for i, line in enumerate(visible_lines):
            # Horizontal scroll: show only the visible part of the line
            display_line = line
            # Calculate the pixel offset for horizontal scrolling
            if horiz_scroll_offset > 0:
                # Find where to start the substring so that the rendered width matches the scroll offset
                px = 0
                char_idx = 0
                while char_idx < len(line) and px < horiz_scroll_offset:
                    px += input_font.size(line[char_idx])[0]
                    char_idx += 1
                display_line = line[char_idx:]
            # Render only the visible part that fits in the box
            rendered = ""
            px = 0
            for ch in display_line:
                ch_width = input_font.size(ch)[0]
                if px + ch_width > input_box_inner_width:
                    break
                rendered += ch
                px += ch_width
            txt_surface = input_font.render(rendered, True, (255, 255, 255))
            screen.blit(txt_surface, (input_box.x + 5, input_box.y + 5 + i * line_height))

        # Draw vertical scrollbar if needed
        if total_lines > max_visible_lines:
            scrollbar_x = input_box.right + 3
            scrollbar_y = input_box.top
            scrollbar_w = 10
            scrollbar_h = input_box.height
            pygame.draw.rect(screen, (80, 80, 80), (scrollbar_x, scrollbar_y, scrollbar_w, scrollbar_h), border_radius=5)
            # Scrollbar handle
            handle_h = max(20, int(scrollbar_h * (max_visible_lines / total_lines)))
            handle_y = scrollbar_y + int((scroll_offset / max(1, total_lines - max_visible_lines)) * (scrollbar_h - handle_h))
            pygame.draw.rect(screen, (180, 180, 180), (scrollbar_x, handle_y, scrollbar_w, handle_h), border_radius=5)

        # Draw horizontal scrollbar if needed (pixel-based)
        max_line_pixel_width = max((input_font.size(line)[0] for line in lines), default=0)
        input_box_inner_width = input_box.width - 10  # 5px padding on each side
        if max_line_pixel_width > input_box_inner_width:
            hscroll_x = input_box.left
            hscroll_y = input_box.bottom + 3
            hscroll_w = input_box.width
            hscroll_h = 10
            pygame.draw.rect(screen, (80, 80, 80), (hscroll_x, hscroll_y, hscroll_w, hscroll_h), border_radius=5)
            # Handle width proportional to visible area
            handle_w = max(20, int(hscroll_w * (input_box_inner_width / max_line_pixel_width)))
            # Handle position proportional to scroll offset
            max_offset = max_line_pixel_width - input_box_inner_width
            handle_x = hscroll_x + int((horiz_scroll_offset / max(1, max_offset)) * (hscroll_w - handle_w))
            pygame.draw.rect(screen, (180, 180, 180), (handle_x, hscroll_y, handle_w, hscroll_h), border_radius=5)

        # Draw Enter button
        pygame.draw.rect(screen, (60, 120, 60), enter_button_rect, border_radius=8)
        screen.blit(
            enter_button_text,
            (
                enter_button_rect.centerx - enter_button_text.get_width() // 2,
                enter_button_rect.centery - enter_button_text.get_height() // 2
            )
        )

        pygame.display.flip()

    pygame.display.quit()
    pygame.quit()

def mainmenu(pgn_string, color, stockfish_path, mistakes,accuracy):
    """
    Displays a Pygame window with a title and up to four vertically aligned buttons:
    'All Game', 'Opening', 'Middlegame', and 'Endgame'.
    Only shows buttons for mistake types that exist.
    """
    pygame.init()
    menu_width, menu_height = 400, 520
    screen = pygame.display.set_mode((menu_width, menu_height))
    pygame.display.set_caption("Choose Mistake Type")
    title_font = pygame.font.SysFont(None, 44)
    font = pygame.font.SysFont(None, 36)
    button_font = pygame.font.SysFont(None, 32)

    # Create button definitions for each available mistake type
    button_defs = []
    if mistakes["all"]:
        button_defs.append((f"All Game: {len(mistakes['all'])}", "all"))
    if mistakes["opening"]:
        button_defs.append((f"Opening: {len(mistakes['opening'])}", "opening"))
    if mistakes["middlegame"]:
        button_defs.append((f"Middlegame: {len(mistakes['middlegame'])}", "middlegame"))
    if mistakes["endgame"]:
        button_defs.append((f"Endgame: {len(mistakes['endgame'])}", "endgame"))

    button_w, button_h = 200, 60
    button_spacing = 25
    start_y = 140
    button_rects = []

    # Create rectangles for each button
    for i, (label, key) in enumerate(button_defs):
        rect = pygame.Rect(
            (menu_width - button_w) // 2,
            start_y + i * (button_h + button_spacing),
            button_w,
            button_h
        )
        button_rects.append((rect, label, key))

    # Create a back button at the bottom left
    back_button_width = int(98)
    back_button_height = int(31.5)
    back_button_x = 20
    back_button_y = menu_height - back_button_height - 10
    back_button_rect = pygame.Rect(back_button_x, back_button_y, back_button_width, back_button_height)
    back_button_font = pygame.font.SysFont(None, 23)
    back_button_text = back_button_font.render("Back", True, (255, 255, 255))

    # Prepare accuracy display
    accuracy_font = pygame.font.SysFont(None, 32)
    accuracy_value = accuracy * 100
    if accuracy_value >= 80:
        accuracy_color = (80, 220, 80)
    elif accuracy_value >= 75:
        accuracy_color = (255, 180, 80)
    else:
        accuracy_color = (220, 80, 80)
    accuracy_text = f"Accuracy: {accuracy_value:.1f}%"

    running = True
    while running:
        screen.fill((40, 40, 40))
        # Draw the main title
        title = title_font.render("Top 3 Chess Mistakes", True, (220, 220, 220))
        screen.blit(title, ((menu_width - title.get_width()) // 2, 30))

        # Draw the accuracy score under the title
        accuracy_surface = accuracy_font.render(accuracy_text, True, accuracy_color)
        screen.blit(accuracy_surface, ((menu_width - accuracy_surface.get_width()) // 2, 75))

        # Draw the subtitle
        subtitle = font.render("Analyze mistakes for:", True, (200, 200, 200))
        screen.blit(subtitle, ((menu_width - subtitle.get_width()) // 2, 110))

        # Draw all available mistake type buttons
        for rect, label, key in button_rects:
            pygame.draw.rect(screen, (80, 80, 80), rect, border_radius=10)
            text = button_font.render(label, True, (255, 255, 255))
            screen.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))

        # Draw the back button
        pygame.draw.rect(screen, (120, 60, 60), back_button_rect, border_radius=8)
        screen.blit(
            back_button_text,
            (
                back_button_rect.centerx - back_button_text.get_width() // 2,
                back_button_rect.centery - back_button_text.get_height() // 2
            )
        )

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                for rect, label, key in button_rects:
                    if rect.collidepoint(mx, my):
                        running = False
                        show_board_at_first_mistake_pygame(pgn_string, color, stockfish_path, key, mistakes,accuracy)
                if back_button_rect.collidepoint(mx, my):
                    running = False
                    # Go back to start window
                    start_window(username, stockfish_path)
                    return

    pygame.display.quit()
    pygame.quit()
def show_board_at_first_mistake_pygame(pgn_string, color, stockfish_path,choice,mistakes_set,accuracy):
    """
    Shows the board at the first 3 mistakes in the sorted mistake list for the given color,
    and highlights the from-square and to-square of the mistake move.
    Use left/right arrow keys or 'a'/'d' to move between mistakes.
    You can interact with the pieces to make legal moves after a mistake; going back resets to the mistake position.
    """
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Board at Mistakes")
    load_piece_images()

    # Get the sorted list of mistakes (up to 3)
    mistakes = mistakes_set[choice] if choice in mistakes_set else []
    if not mistakes:
        print("No mistakes found.")
        pygame.quit()
        return
    # For each mistake, replay the game up to and including the mistake move, and track the move object and board
    game = chess.pgn.read_game(io.StringIO(pgn_string))
    all_moves = list(game.mainline_moves())
    mistake_positions = []
    prev_mistake_positions = []

    for move_number, move_san, eval_score, change in mistakes:
        board = game.board()
        mistake_move = None
        for move in all_moves:
            san = board.san(move)
            current_move_number = board.fullmove_number
            side = "white" if board.turn == chess.WHITE else "black"
            if san == move_san and current_move_number == move_number and side == color:
                mistake_move = move
                prev_mistake_positions.append((board.copy()))
                board.push(move)
                break
            board.push(move)
        mistake_positions.append((board.copy(), mistake_move, move_number, move_san, eval_score, change))
    # Highlight color for move squares
    highlight_square = pygame.Color(210, 180, 140, 90)  # light brown (tan), semi-transparent

    def draw_board_with_highlight(screen, board, player_color, move, mistake_info, idx, total, selected_square=None, legal_moves=[]):
        # Clear the whole window before drawing
        screen.fill((40, 40, 40))  # Fill window background with dark grey

        # Draw rectangles for side panels
        pygame.draw.rect(
            screen,
            (30, 30, 30),  # dark grey (left half of side panel)
            pygame.Rect(BOARD_SIZE, 0, SIDE_PANEL_WIDTH // 2, WINDOW_HEIGHT)
        )
        pygame.draw.rect(
            screen,
            (0, 0, 0),  # black (right half of side panel)
            pygame.Rect(BOARD_SIZE + SIDE_PANEL_WIDTH // 2, 0, SIDE_PANEL_WIDTH // 2, WINDOW_HEIGHT)
        )

        # Draw evaluation score label at the top of the left side of side panel
        eval_panel_font = pygame.font.SysFont(None, int(32))
        eval_label = "Current evaluation score"
        eval_label_surface = eval_panel_font.render(eval_label, True, (220, 220, 220))
        screen.blit(
            eval_label_surface,
            (BOARD_SIZE + 20, 20)
        )

        # Draw main board (shift board down by EXTRA_HEIGHT)
        colors = [pygame.Color(181, 136, 99), pygame.Color(240, 217, 181)]
        for rank in range(8):
            for file in range(8):
                display_rank = rank if player_color == "white" else 7 - rank
                display_file = file if player_color == "white" else 7 - file
                color = colors[(display_rank + display_file) % 2]
                pygame.draw.rect(
                    screen,
                    color,
                    pygame.Rect(
                        file * SQUARE_SIZE,
                        EXTRA_HEIGHT + (7 - rank) * SQUARE_SIZE,
                        SQUARE_SIZE,
                        SQUARE_SIZE
                    )
                )
        # Draw blank rectangle for side panel
        pygame.draw.rect(
            screen,
            (30, 30, 30),  # dark grey
            pygame.Rect(BOARD_SIZE, 0, SIDE_PANEL_WIDTH, WINDOW_HEIGHT)
        )

        # Draw navigation and action buttons on the right side of the side panel
        button_width = 70
        button_height = 25
        right_panel_x = BOARD_SIZE + SIDE_PANEL_WIDTH // 2
        right_panel_width = SIDE_PANEL_WIDTH // 2

        font = pygame.font.SysFont(None, 20)

        # Spacing between buttons
        spacing = 20

        # Calculate total height of all buttons and spacings
        retry_button_width = button_width * 2
        retry_button_height = button_height * 2
        best_button_width = retry_button_width
        best_button_height = retry_button_height

        total_buttons_height = (
            retry_button_height +
            spacing +
            best_button_height +
            spacing +
            button_height +  # prev
            spacing +
            button_height    # next
        )

        # Start y so that all buttons are 5% away from the bottom of the right panel
        start_y = int(WINDOW_HEIGHT - (total_buttons_height + int(WINDOW_HEIGHT * 0.05)))

        # Retry button: centered on right side
        retry_button_x = right_panel_x + (right_panel_width - retry_button_width) // 2
        retry_button_rect = pygame.Rect(
            retry_button_x,
            start_y,
            retry_button_width,
            retry_button_height
        )
        # Best button: centered, below retry
        best_button_x = right_panel_x + (right_panel_width - best_button_width) // 2
        best_button_rect = pygame.Rect(
            best_button_x,
            retry_button_rect.bottom + spacing,
            best_button_width,
            best_button_height
        )
        # Previous button: move to right side of side panel, aligned with next button
        prev_button_rect = pygame.Rect(
            right_panel_x + 20,
            WINDOW_HEIGHT - button_height - 20,
            button_width,
            button_height
        )
        # Next button: right, bottom of right side panel (unchanged)
        next_button_rect = pygame.Rect(
            right_panel_x + right_panel_width - button_width - 20,
            WINDOW_HEIGHT - button_height - 20,
            button_width,
            button_height
        )

        pygame.draw.rect(screen, (80, 80, 80), prev_button_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 80, 80), next_button_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 80, 80), retry_button_rect, border_radius=8)
        pygame.draw.rect(screen, (80, 80, 80), best_button_rect, border_radius=8)
        prev_text = font.render("Previous", True, (220, 220, 220))
        next_text = font.render("Next", True, (220, 220, 220))
        retry_font = pygame.font.SysFont(None, 40)
        retry_text = retry_font.render("Retry", True, (220, 220, 220))
        best_font = pygame.font.SysFont(None, 40)
        best_text = best_font.render("Best", True, (220, 220, 220))
        screen.blit(prev_text, (prev_button_rect.centerx - prev_text.get_width() // 2, prev_button_rect.centery - prev_text.get_height() // 2))
        screen.blit(next_text, (next_button_rect.centerx - next_text.get_width() // 2, next_button_rect.centery - next_text.get_height() // 2))
        screen.blit(retry_text, (retry_button_rect.centerx - retry_text.get_width() // 2, retry_button_rect.centery - retry_text.get_height() // 2))
        screen.blit(best_text, (best_button_rect.centerx - best_text.get_width() // 2, best_button_rect.centery - best_text.get_height() // 2))

        # Draw up to 3 boxes with mistake moves on the left side of the side panel
        mistake_box_height = retry_button_height
        mistake_box_width = 180  # Width for move text
        mistake_box_x = BOARD_SIZE + 20  # Padding from left edge of side panel

        # Move the boxes down so the top box aligns with the retry button
        box_start_y = retry_button_rect.y

        num_boxes = min(3, len(mistake_positions))  # Only draw as many as exist, up to 3

        for i in range(num_boxes):
            move_number, move_san = mistake_positions[i][2], mistake_positions[i][3]
            mistake_text = f"{move_number}. {move_san}"
            box_y = box_start_y + i * (mistake_box_height + 20)
            # Highlight the current mistake box
            if i == idx:
                box_color = (160, 120, 60)  # highlighted brown
                text_color = (0, 0, 0)
            else:
                box_color = (60, 60, 60)    # normal grey
                text_color = (255, 255, 255)
            # Draw the box
            pygame.draw.rect(
                screen,
                box_color,
                pygame.Rect(mistake_box_x, box_y, mistake_box_width, mistake_box_height),
                border_radius=8
            )
            # Draw the move text
            mistake_font = pygame.font.SysFont(None, 28)
            mistake_text_surface = mistake_font.render(mistake_text, True, text_color)
            screen.blit(
                mistake_text_surface,
                (
                    mistake_box_x + (mistake_box_width - mistake_text_surface.get_width()) // 2,
                    box_y + (mistake_box_height - mistake_text_surface.get_height()) // 2
                )
            )

        # Highlight move squares
        if move and board.move_stack and board.move_stack[-1] == move:
            # Only highlight the mistake move if the last move on the board is the mistake move
            from_sq = move.from_square
            to_sq = move.to_square
            from_file = chess.square_file(from_sq)
            from_rank = chess.square_rank(from_sq)
            to_file = chess.square_file(to_sq)
            to_rank = chess.square_rank(to_sq)
            # Flip for orientation
            display_from_file = from_file if player_color == "white" else 7 - from_file
            display_from_rank = from_rank if player_color == "white" else 7 - from_rank
            display_to_file = to_file if player_color == "white" else 7 - to_file
            display_to_rank = to_rank if player_color == "white" else 7 - to_rank
            # Draw highlight on both squares
            pygame.draw.rect(
                screen,
                highlight_square,
                pygame.Rect(
                    display_from_file * SQUARE_SIZE,
                    EXTRA_HEIGHT + (7 - display_from_rank) * SQUARE_SIZE,
                    SQUARE_SIZE,
                    SQUARE_SIZE
                )
            )
            pygame.draw.rect(
                screen,
                highlight_square,
                pygame.Rect(
                    display_to_file * SQUARE_SIZE,
                    EXTRA_HEIGHT + (7 - display_to_rank) * SQUARE_SIZE,
                    SQUARE_SIZE,
                    SQUARE_SIZE
                )
            )
        # Highlight last move squares
        if board.move_stack:
            last_move = board.move_stack[-1]
            from_sq = last_move.from_square
            to_sq = last_move.to_square
            from_file = chess.square_file(from_sq)
            from_rank = chess.square_rank(from_sq)
            to_file = chess.square_file(to_sq)
            to_rank = chess.square_rank(to_sq)
            # Flip for orientation
            display_from_file = from_file if player_color == "white" else 7 - from_file
            display_from_rank = from_rank if player_color == "white" else 7 - from_rank
            display_to_file = to_file if player_color == "white" else 7 - to_file
            display_to_rank = to_rank if player_color == "white" else 7 - to_rank
            # Draw highlight on both squares
            pygame.draw.rect(
                screen,
                highlight_square,
                pygame.Rect(
                    display_from_file * SQUARE_SIZE,
                    EXTRA_HEIGHT + (7 - display_from_rank) * SQUARE_SIZE,
                    SQUARE_SIZE,
                    SQUARE_SIZE
                )
            )
            pygame.draw.rect(
                screen,
                highlight_square,
                pygame.Rect(
                    display_to_file * SQUARE_SIZE,
                    EXTRA_HEIGHT + (7 - display_to_rank) * SQUARE_SIZE,
                    SQUARE_SIZE,
                    SQUARE_SIZE
                )
            )
        # Highlight selected square
        if selected_square is not None:
            file = chess.square_file(selected_square)
            rank = chess.square_rank(selected_square)
            display_file = file if player_color == "white" else 7 - file
            display_rank = rank if player_color == "white" else 7 - rank
            pygame.draw.rect(
                screen,
                highlight_square,
                pygame.Rect(
                    display_file * SQUARE_SIZE,
                    EXTRA_HEIGHT + (7 - display_rank) * SQUARE_SIZE,
                    SQUARE_SIZE,
                    SQUARE_SIZE
                )
            )
            # Draw transparent grey dots or rings for legal moves
            for move in legal_moves:
                to_sq = move.to_square
                to_file = chess.square_file(to_sq)
                to_rank = chess.square_rank(to_sq)
                display_to_file = to_file if player_color == "white" else 7 - to_file
                display_to_rank = to_rank if player_color == "white" else 7 - to_rank
                center_x = display_to_file * SQUARE_SIZE + SQUARE_SIZE // 2
                center_y = EXTRA_HEIGHT + (7 - display_to_rank) * SQUARE_SIZE + SQUARE_SIZE // 2
                # Draw a ring for capture
                ring_outer_radius = int(SQUARE_SIZE * 0.5 * 0.95)
                ring_inner_radius = int(SQUARE_SIZE * 0.3)
                if board.piece_at(to_sq) and board.piece_at(to_sq).color != board.turn:
                    ring_surface = pygame.Surface((SQUARE_SIZE, SQUARE_SIZE), pygame.SRCALPHA)
                    ring_thickness = max(2, int((ring_outer_radius - ring_inner_radius) * 0.5))
                    pygame.draw.circle(
                        ring_surface, (120, 120, 120, 80),
                        (SQUARE_SIZE // 2, SQUARE_SIZE // 2),
                        ring_outer_radius, width=ring_thickness
                    )
                    screen.blit(ring_surface, (center_x - SQUARE_SIZE // 2, center_y - SQUARE_SIZE // 2))
                else:
                    # Draw a dot for normal move
                    radius = SQUARE_SIZE // 6
                    dot_surface = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
                    pygame.draw.circle(dot_surface, (120, 120, 120, 60), (radius, radius), radius)
                    screen.blit(dot_surface, (center_x - radius, center_y - radius))
        # Draw pieces
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                color_piece = 'w' if piece.color == chess.WHITE else 'b'
                img = PIECE_IMAGES[color_piece + piece.symbol().lower()]
                file = chess.square_file(square)
                rank = chess.square_rank(square)
                display_file = file if player_color == "white" else 7 - file
                display_rank = rank if player_color == "white" else 7 - rank
                screen.blit(
                    img,
                    (display_file * SQUARE_SIZE, EXTRA_HEIGHT + (7 - display_rank) * SQUARE_SIZE)
                )
        # Evaluate the current board for display
        with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
            eval_turn = chess.WHITE if player_color == "white" else chess.BLACK
            current_eval = evaluate_fen(board.fen(), engine, eval_turn)

            eval_value_font = pygame.font.SysFont(None, 28)
        try:
            eval_float = float(current_eval)
            eval_value_str = f"{eval_float:.2f}"
        except Exception:
            eval_value_str = str(current_eval)
        eval_value_surface = eval_value_font.render(eval_value_str, True, (255, 255, 255))
        screen.blit(
            eval_value_surface,
            (BOARD_SIZE + 20, 60)
        )
        # Show best 3 lines for current position below the evaluation line
        best_lines = []
        try:
            with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
                info = engine.analyse(board, chess.engine.Limit(time=0.5), multipv=3)
                for i, pv_info in enumerate(info):
                    pv = pv_info.get("pv")
                    if pv:
                        pv_board = board.copy()
                        pv_moves = []
                        for m in pv[:6]:
                            pv_moves.append(pv_board.san(m))
                            pv_board.push(m)
                        pv_score = pv_info["score"].white().score(mate_score=10000)
                        pv_text = f"{i+1}: {' '.join(pv_moves)} (Eval: {pv_score/100 if pv_score < 10000 else '#'} )"
                        best_lines.append(pv_text)
        except ValueError:
          print('Error with lines')

        # Add button to reveal/hide best 3 lines below evaluation
        lines_button_width = 120
        lines_button_height = 32
        lines_button_x = BOARD_SIZE + 20
        lines_button_y = 90  # Just below eval value
        lines_button_rect = pygame.Rect(
            lines_button_x,
            lines_button_y,
            lines_button_width,
            lines_button_height
        )
        lines_button_font = pygame.font.SysFont(None, 24)
        # Use an attribute on the function to store state (default hidden)
        if not hasattr(draw_board_with_highlight, "show_lines"):
            draw_board_with_highlight.show_lines = False
        lines_button_text = "Show Lines" if not draw_board_with_highlight.show_lines else "Hide Lines"
        lines_button_surface = lines_button_font.render(lines_button_text, True, (255, 255, 255))
        pygame.draw.rect(screen, (80, 80, 80), lines_button_rect, border_radius=8)
        screen.blit(
            lines_button_surface,
            (
                lines_button_rect.centerx - lines_button_surface.get_width() // 2,
                lines_button_rect.centery - lines_button_surface.get_height() // 2
            )
        )

        # Only show best lines if revealed
        if draw_board_with_highlight.show_lines:
            best_line_font = pygame.font.SysFont(None, 22)
            i=0
            for line in best_lines:
                line_surface = best_line_font.render(line, True, (255, 255, 255))  # White font color
                screen.blit(
                    line_surface,
                    (BOARD_SIZE + 20, lines_button_rect.bottom + 10 + i * 28)
                )
                i += 1  # Increment line index for spacing

        # Calculate change from the original eval at the mistake
        original_eval = mistake_info[2]
        try:
            eval_float = float(current_eval)
            orig_eval_float = float(original_eval)
            current_change = eval_float - orig_eval_float
            eval_str = f"{eval_float:.2f}"
            change_str = f"{current_change:+.2f}"
        except Exception:
            eval_str = str(current_eval)
            change_str = "N/A"

        move_number, move_san = mistake_info[0], mistake_info[1]
        # Custom title based on choice
        phase_title = {
            "all": "All Game",
            "opening": "Opening",
            "middlegame": "Middlegame",
            "endgame": "Endgame"
        }.get(choice, "All Game")
        custom_title = f"{phase_title} Mistake {idx+1} : {move_number}. {move_san}"
        font_title = pygame.font.SysFont(None, 36)
        title_surface = font_title.render(custom_title, True, (220, 220, 220))
        screen.blit(title_surface, (10, 20))  # Top left, increased spacing

        # Add a "Return to Start" button below the board
        return_button_width = int(200 * 0.8)
        return_button_height = int(45 * 0.8)
        return_button_x = 10
        return_button_y = EXTRA_HEIGHT + BOARD_SIZE + 10
        return_button_rect = pygame.Rect(return_button_x, return_button_y, return_button_width, return_button_height)
        return_button_font = pygame.font.SysFont(None, 24)
        return_button_text = return_button_font.render("Return to Start", True, (255, 255, 255))
        pygame.draw.rect(screen, (60, 120, 60), return_button_rect, border_radius=8)
        screen.blit(
            return_button_text,
            (
                return_button_rect.centerx - return_button_text.get_width() // 2,
                return_button_rect.centery - return_button_text.get_height() // 2
            )
        )

        # Highlight the return button on hover
        if return_button_rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(screen, (80, 160, 80), return_button_rect, border_radius=8)

        # Draw a "Back" button at the top right of the side panel
        back_button_width = 100
        back_button_height = 40
        back_button_x = BOARD_SIZE + SIDE_PANEL_WIDTH - back_button_width - 20
        back_button_y = 20
        back_button_rect = pygame.Rect(back_button_x, back_button_y, back_button_width, back_button_height)
        back_button_font = pygame.font.SysFont(None, 28)
        back_button_text = back_button_font.render("Back", True, (255, 255, 255))
        pygame.draw.rect(screen, (120, 60, 60), back_button_rect, border_radius=8)
        screen.blit(
            back_button_text,
            (
                back_button_rect.centerx - back_button_text.get_width() // 2,
                back_button_rect.centery - back_button_text.get_height() // 2
            )
        )

        return prev_button_rect, next_button_rect, retry_button_rect, best_button_rect,lines_button_rect,back_button_rect,return_button_rect

    idx = 0
    total = len(mistake_positions)
    # For interactive play, keep a working board for each mistake position
    working_boards = [pos[0].copy() for pos in mistake_positions]
    prev_working_boards = [prev_pos.copy() for prev_pos in prev_mistake_positions]
    selected_square = None
    legal_moves = []
    running = True
    show_best = False
    best_move = None
    prev=0
    while running:
        if prev==0:
            board = working_boards[idx]
        else:
            board = prev_working_boards[idx]
        mistake_move = mistake_positions[idx][1]
        move_number, move_san, eval_score, change = mistake_positions[idx][2:6]
        prev_button_rect, next_button_rect, retry_button_rect, best_button_rect,lines_button_rect,back_button_rect,return_button_rect = draw_board_with_highlight(
            screen, board, player_color=color, move=mistake_move,
            mistake_info=(move_number, move_san, eval_score, change), idx=idx, total=total,
            selected_square=selected_square, legal_moves=legal_moves
        )
        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                # Arrow keys do nothing now
                if event.key == pygame.K_ESCAPE:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = event.pos
                # Check if next/previous/retry/best button clicked
                if prev_button_rect.collidepoint(mouse_x, mouse_y):
                    idx = (idx - 1) % total
                    working_boards[idx] = mistake_positions[idx][0].copy()
                    selected_square = None
                    legal_moves = []
                    show_best = False
                    prev=0
                elif next_button_rect.collidepoint(mouse_x, mouse_y):
                    idx = (idx + 1) % total
                    working_boards[idx] = mistake_positions[idx][0].copy()
                    selected_square = None
                    legal_moves = []
                    show_best = False
                    prev=0
                elif retry_button_rect.collidepoint(mouse_x, mouse_y):
                    # Reset to position before the mistake (always even index)
                    prev_working_boards[idx] = prev_mistake_positions[idx].copy()
                    selected_square = None
                    legal_moves = []
                    show_best = False
                    prev=1
                elif best_button_rect.collidepoint(mouse_x, mouse_y):
                    # Show the best move instead of the mistake
                    # Find the board before the mistake
                    board_before = prev_mistake_positions[idx].copy()
                    with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
                        result = engine.play(board_before, chess.engine.Limit(time=0.2))
                        best_move = result.move
                    if best_move:
                        prev_working_boards[idx] = board_before.copy()
                        prev_working_boards[idx].push(best_move)
                        selected_square = None
                        legal_moves = []
                        show_best = True
                        prev=1
                elif lines_button_rect.collidepoint(mouse_x, mouse_y):
                    draw_board_with_highlight.show_lines = not draw_board_with_highlight.show_lines
                elif back_button_rect.collidepoint(mouse_x, mouse_y):
                    # Return to main menu
                    running = False
                    mainmenu(pgn_string, color, stockfish_path,mistakes_set,accuracy)
                    # Optionally, break or return a value to signal main() to show menu again
                elif return_button_rect.collidepoint(mouse_x, mouse_y):
                    running = False
                    # Call start_window to return to the PGN entry screen
                    start_window(username, stockfish_path)
                    return  # Prevent further drawing after quitting
                # Only allow clicks on the board area
                elif (0 <= mouse_x < BOARD_SIZE) and (EXTRA_HEIGHT <= mouse_y < EXTRA_HEIGHT + BOARD_SIZE):
                    file = mouse_x // SQUARE_SIZE
                    rank = 7 - ((mouse_y - EXTRA_HEIGHT) // SQUARE_SIZE)
                    # Flip for orientation
                    if color == "black":
                        file = 7 - file
                        rank = 7 - rank
                    square = chess.square(file, rank)
                    piece = board.piece_at(square)
                    if selected_square is None:
                        # Select a piece if it belongs to the player to move
                        if piece and piece.color == board.turn:
                            selected_square = square
                            # Show legal moves for this piece
                            legal_moves = [m for m in board.legal_moves if m.from_square == square]
                        else:
                            selected_square = None
                            legal_moves = []
                    else:
                        # Try to make a move
                        move = None
                        for m in legal_moves:
                            if m.to_square == square:
                                move = m
                                break
                        if move:
                            board.push(move)
                        # Reset selection after move attempt
                        selected_square = None
                        legal_moves = []
    pygame.display.quit()
    pygame.quit()
    

# Example usage:

#code
#intilaize username
username = "yorubap"
#start code
start_window(username,STOCKFISH_PATH)







