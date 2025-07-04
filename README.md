# Top-3-Chess-Mistakes

A lightweight dashboard app that allows users to visualise, analyse, and  interact with  the top 3 mistakes of chess game, or game phases. 
---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

---

## Features

- Visual top 3 mistakes in order of severity
- Supports uploading .pgn text
- Interactive board for further analysis
- Simple dashboard layout using [pygame]*
- Retry and Answer button to allow another attempt at mistake
- Error messages for incorrect input
- Automatically analyses from inputted username



---

## Installation

### Clone the repo:
```bash
git clone https://github.com/johnblessmbunga/Top-3-Chess-Mistakes.git
cd Top-3-Chess-Mistakes
```
Optional change username manually:username = "Example User Name"

### Virtual Environment Setup

Create and activate the environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows
```
### Install dependicies

```bash
pip install chess
pip install pygame
pip install pyperclip
```
install assets from asset folder
### Install Stockfish
```bash
sudo apt install stockfish  # Debian/Ubuntu
brew install stockfish      # macOS (Homebrew)
```
Download from [stockfishchess.org](https://stockfishchess.org/) for Windows
---
## Usage
### 1 Launch Dashboard
```bash
run Top-3-Chess-Mistakes.py
```
### 2 Upload PGN
<p align="center">
  <img src="screenshots/PGN_insert.png" width="500" alt="PGN"/>
  <br/>
  <em>Figure 1: Start Window for PGN insert </em>
</p>

1. Copy PGN of game
2. Paste PGN in blue area
3. Press Enter or click enter button

### 3 Choose Game Stage to View
<p align="center">
  <img src="screenshots/Main_menu.png" width="500" alt="Main"/>
  <br/>
  <em>Figure 2: Main menu for choosing game stage </em>
</p>

1. All
2. Opening
3. Middlegame
4. Endgame

Note if no mistakes detected in a stage the stage will not appear on this page

### 4 Analyse and Retry Mistakes
<p align="center">
  <img src="screenshots/Mistake_panel.png" width="500" alt="Mistake"/>
  <br/>
  <em>Figure 2: Main menu for choosing game stage </em>
</p>

- Press Retry button for another attempt at mistake
- Press Best buttoon to find best move instead of mistake
- Press Show Lines button to reveal further moves
- Interact with board to play legal moves
- Press Next or Previous buttons to switch to different mistake positions
  
### 5 New Analysis
- Use Back button to return to main menu  for analysis in different game stage
- Use Return to Start button to insert new PGN
---
## License
This project is licensed under the MIT License. See LICENSE for more information






