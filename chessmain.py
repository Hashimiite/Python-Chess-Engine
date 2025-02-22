import pygame as p
import ChessEngine
import ChessAI
import sys
import random
from multiprocessing import Process, Queue
import random

# Game constants
BOARD_WIDTH = BOARD_HEIGHT = 512
MOVE_LOG_PANEL_WIDTH = 250
MOVE_LOG_PANEL_HEIGHT = BOARD_HEIGHT
DIMENSION = 8
SQUARE_SIZE = BOARD_HEIGHT // DIMENSION
MAX_FPS = 15
IMAGES = {}

# Color scheme
MENU_BG = (42, 42, 42)
BOARD_COLORS = [(240, 217, 181), (181, 136, 99)]
HIGHLIGHT_COLOR = (42, 157, 143, 100)
LAST_MOVE_COLOR = (233, 196, 106, 100)
BUTTON_COLORS = {
    'normal': (38, 70, 83),
    'hover': (42, 157, 143),
    'press': (231, 111, 81)
}

def load_images():
    """Load images for chess pieces"""
    pieces = ['wp', 'wR', 'wN', 'wB', 'wK', 'wQ', 'bp', 'bR', 'bN', 'bB', 'bK', 'bQ']
    for piece in pieces:
        IMAGES[piece] = p.transform.scale(p.image.load(f"images/{piece}.png"), (SQUARE_SIZE, SQUARE_SIZE))

class Button:#Modern button component with hover and click effects
    def __init__(self, x, y, w, h, text, radius=10):
        self.rect = p.Rect(x, y, w, h)
        self.text = text
        self.radius = radius
        self.state = 'normal'
        self.clicked = False

    def draw(self, surface, font):#Draw button with current state
        color = BUTTON_COLORS[self.state]
        p.draw.rect(surface, color, self.rect, border_radius=self.radius)
        p.draw.rect(surface, (255, 255, 255), self.rect, 2, self.radius)
        text_surf = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):#pdate button state based on events
        if event.type == p.MOUSEMOTION:
            self.state = 'hover' if self.rect.collidepoint(event.pos) else 'normal'
        elif event.type == p.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.state = 'press'
                self.clicked = True
        elif event.type == p.MOUSEBUTTONUP:
            if self.clicked and self.rect.collidepoint(event.pos):
                self.clicked = False
                self.state = 'normal'
                return True
            self.clicked = False
            self.state = 'normal'
        return False

def draw_board(screen):# Draw the chess board squares
    for row in range(DIMENSION):
        for col in range(DIMENSION):
            color = BOARD_COLORS[(row + col) % 2]
            p.draw.rect(screen, color, p.Rect(col*SQUARE_SIZE, row*SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))

def draw_pieces(screen, board):#Draw the chess pieces on the board
    for row in range(DIMENSION):
        for col in range(DIMENSION):
            piece = board[row][col]
            if piece != "--":
                screen.blit(IMAGES[piece], (col*SQUARE_SIZE, row*SQUARE_SIZE))

def draw_menu(screen):#Draw animated main menu with particles and buttons
    screen.fill(MENU_BG)
    
    # Animated particles
    for _ in range(50):
        x = random.randint(0, BOARD_WIDTH)
        y = random.randint(0, BOARD_HEIGHT)
        p.draw.circle(screen, (100, 100, 100), (x, y), 2)
    # Title
    title_font = p.font.SysFont('Arial', 72, True)
    title_text = title_font.render('CHESS', True, (231, 111, 81))
    title_rect = title_text.get_rect(center=(BOARD_WIDTH//2, 100))
    screen.blit(title_text, title_rect)
    # Create buttons
    button_font = p.font.SysFont('Arial', 32, True)
    buttons = [
        Button(BOARD_WIDTH//2-150, 200, 300, 60, "Player vs Player"),
        Button(BOARD_WIDTH//2-150, 280, 300, 60, "Player vs AI")
    ]

    # Draw buttons
    for btn in buttons:
        btn.draw(screen, button_font)

    return buttons


def animate_move(move, screen, board, clock): # Animate piece movement
    d_row = move.end_row - move.start_row
    d_col = move.end_col - move.start_col
    frames = 10
    for frame in range(frames + 1):
        progress = frame / frames
        x = move.start_col * SQUARE_SIZE + d_col * SQUARE_SIZE * progress
        y = move.start_row * SQUARE_SIZE + d_row * SQUARE_SIZE * progress
        draw_board(screen)
        draw_pieces(screen, board)
        screen.blit(IMAGES[move.piece_moved], (x, y))
        p.display.flip()
        clock.tick(60)

def draw_move_log(screen, game_state, font): # Draw the move log panel
    move_log_rect = p.Rect(BOARD_WIDTH, 0, MOVE_LOG_PANEL_WIDTH, MOVE_LOG_PANEL_HEIGHT)
    p.draw.rect(screen, p.Color('black'), move_log_rect)
    
    move_log = game_state.move_log
    move_texts = []
    for i in range(0, len(move_log), 2):
        move_string = f"{i//2 + 1}. {move_log[i]}"
        if i + 1 < len(move_log):
            move_string += f"  {move_log[i+1]}"
        move_texts.append(move_string)
    
    padding = 5
    text_y = padding
    for text in move_texts:
        text_surface = font.render(text, True, p.Color('white'))
        screen.blit(text_surface, (BOARD_WIDTH + padding, text_y))
        text_y += text_surface.get_height() + 2

def game_loop(screen, clock, mode, player_color=None): # Handles both Player vs Player and Player vs AI modes.
    game_state = ChessEngine.GameState()
    valid_moves = game_state.getValidMoves()
    selected_square = ()
    player_clicks = []
    ai_thinking = False
    move_finder_process = None
    game_over = False

    while True:
        # Determine if its a human's turn
        human_turn = (mode == "pvp") or (
            (game_state.white_to_move and player_color == "white") or
            (not game_state.white_to_move and player_color == "black")
        )

        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit()
                sys.exit()

            elif e.type == p.MOUSEBUTTONDOWN and not game_over and human_turn:
                location = p.mouse.get_pos()
                col = location[0] // SQUARE_SIZE
                row = location[1] // SQUARE_SIZE

                if selected_square == (row, col):
                    selected_square = ()
                    player_clicks = []
                else:
                    selected_square = (row, col)
                    player_clicks.append(selected_square)

                if len(player_clicks) == 2:
                    move = ChessEngine.Move(player_clicks[0], player_clicks[1], game_state.board)
                    if move in valid_moves:
                        game_state.makeMove(move)
                        animate_move(move, screen, game_state.board, clock)
                        selected_square = ()
                        player_clicks = []
                        valid_moves = game_state.getValidMoves()
                    else:
                        player_clicks = [selected_square]

            elif e.type == p.KEYDOWN:
                if e.key == p.K_z:
                    game_state.undoMove()
                    valid_moves = game_state.getValidMoves()
                if e.key == p.K_r:
                    return "menu"

        # AI Move
        if mode == "pvai" and not human_turn and not game_over:
            if not ai_thinking:
                ai_thinking = True
                return_queue = Queue()
                move_finder_process = Process(target=ChessAI.findBestMove, 
                                              args=(game_state, valid_moves, return_queue))
                move_finder_process.start()

            if move_finder_process and not move_finder_process.is_alive():
                ai_move = return_queue.get()
                if ai_move:
                    game_state.makeMove(ai_move)
                ai_thinking = False
                valid_moves = game_state.getValidMoves()

        # Draw board, pieces, and highlights
        draw_board(screen)
        draw_pieces(screen, game_state.board)
        highlight_moves(screen, valid_moves, selected_square)

        draw_move_log(screen, game_state, p.font.SysFont("Arial", 14))

        if game_state.checkmate or game_state.stalemate:
            game_over = True
            text = "Checkmate!" if game_state.checkmate else "Stalemate!"
            font = p.font.SysFont("Helvetica", 32, True)
            text_surface = font.render(text, True, p.Color('red'))
            screen.blit(text_surface, (BOARD_WIDTH/2 - text_surface.get_width()/2, BOARD_HEIGHT/2 - text_surface.get_height()/2))

        p.display.flip()
        clock.tick(MAX_FPS)


def highlight_moves(screen, valid_moves, selected_square):
    """
    Highlights valid moves and selected piece with a strong yellowish color.
    """
    if selected_square:
        row, col = selected_square
        s = p.Surface((SQUARE_SIZE, SQUARE_SIZE), p.SRCALPHA)
        s.fill((255, 215, 0, 180))  # Gold-like yellow for selected piece
        screen.blit(s, (col * SQUARE_SIZE, row * SQUARE_SIZE))

        for move in valid_moves:
            if move.start_row == row and move.start_col == col:
                highlight_surf = p.Surface((SQUARE_SIZE, SQUARE_SIZE), p.SRCALPHA)
                highlight_surf.fill((255, 255, 153, 180))  # Soft yellow for available moves
                screen.blit(highlight_surf, (move.end_col * SQUARE_SIZE, move.end_row * SQUARE_SIZE))



def main():
    p.init()
    screen = p.display.set_mode((BOARD_WIDTH + MOVE_LOG_PANEL_WIDTH, BOARD_HEIGHT))
    p.display.set_caption("Modern Chess")
    clock = p.time.Clock()
    load_images()

    # Choose Game Mode
    current_screen = "mode_selection"
    game_mode = None  
    player_color = None  
    mode_buttons = [
        Button(BOARD_WIDTH // 2 - 150, 200, 300, 60, "Player vs Player"),
        Button(BOARD_WIDTH // 2 - 150, 280, 300, 60, "Player vs AI")
    ]
    # Choose Color (if AI mode is chosen)
    color_buttons = [
        Button(BOARD_WIDTH // 2 - 150, 200, 300, 60, "Play as White"),
        Button(BOARD_WIDTH // 2 - 150, 280, 300, 60, "Play as Black")
    ]
    # mebu animation  for the menu
    stars = [(random.randint(0, BOARD_WIDTH), random.randint(0, BOARD_HEIGHT)) for _ in range(50)]

    while True:
        screen.fill(MENU_BG)
        # Draw moving stars animation
        for i, (x, y) in enumerate(stars):
            p.draw.circle(screen, (100, 100, 100), (x, y), 2)
            stars[i] = (x, (y + 1) % BOARD_HEIGHT)  
        # Draw game title
        title_font = p.font.SysFont('Arial', 72, True)
        title_text = title_font.render('CHESS', True, (231, 111, 81))
        title_rect = title_text.get_rect(center=(BOARD_WIDTH//2, 100))
        screen.blit(title_text, title_rect)

        for e in p.event.get():
            if e.type == p.QUIT:
                p.quit()
                sys.exit()
            #Choose Game Mode
            if current_screen == "mode_selection":
                for btn in mode_buttons:
                    if btn.handle_event(e):
                        if btn.text == "Player vs Player":
                            game_mode = "pvp"
                            current_screen = "game"
                        else:
                            game_mode = "pvai"
                            current_screen = "color_selection"

            #choose Player Color (for AI mode only)
            elif current_screen == "color_selection":
                for btn in color_buttons:
                    if btn.handle_event(e):
                        player_color = "white" if btn.text == "Play as White" else "black"
                        current_screen = "game"

        # Draw UI based on current_screen
        if current_screen == "mode_selection":
            for btn in mode_buttons:
                btn.draw(screen, p.font.SysFont('Arial', 32, True))
        elif current_screen == "color_selection":
            for btn in color_buttons:
                btn.draw(screen, p.font.SysFont('Arial', 32, True))
        elif current_screen == "game":
            current_screen = game_loop(
                screen, clock, game_mode, 
                player_color if game_mode == "pvai" else None  # Only pass color for AI games
            )
        p.display.flip()
        clock.tick(MAX_FPS)

if __name__ == "__main__":
    main()
