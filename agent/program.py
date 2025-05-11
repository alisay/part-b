# COMP30024 Artificial Intelligence, Semester 1 2025
# Project Part B: Game Playing Agent

from referee.game import PlayerColor, Coord, Direction, \
    Action, MoveAction, GrowAction

import random

class Agent:
    """
    This class is the "entry point" for your agent, providing an interface to
    respond to various Freckers game events.
    """

    def __init__(self, color: PlayerColor, **referee: dict):
        """
        This constructor method runs when the referee instantiates the agent.
        Any setup and/or precomputation should be done here.
        """
        self._color = color
        match color:
            case PlayerColor.RED:
                print("Testing: I am playing as RED")
            case PlayerColor.BLUE:
                print("Testing: I am playing as BLUE")

        # Starting frog positions
        self.red_frogs = {Coord(0, i) for i in range(1, 7)}
        self.blue_frogs = {Coord(7, i) for i in range(1, 7)}

        # Determine own and opponent frogs
        self.frogs = self.red_frogs if self._color == PlayerColor.RED else self.blue_frogs
        self.opponent_frogs = self.blue_frogs if self._color == PlayerColor.RED else self.red_frogs

        # Starting lily pads
        self.lily_pads = {
            Coord(0, 0), Coord(0, 7),
            *{Coord(1, c) for c in range(1, 7)},
            *{Coord(6, c) for c in range(1, 7)},
            Coord(7, 0), Coord(7, 7)
        }            
        
    def action(self, **referee: dict) -> Action:
        # Try all possible random MOVE actions first
        possible_moves = []

        if self._color == PlayerColor.RED:
            allowed_directions = {
                Direction.Right, Direction.Left,
                Direction.Down, Direction.DownLeft, Direction.DownRight
            }
        else:  # BLUE
            allowed_directions = {
                Direction.Right, Direction.Left,
                Direction.Up, Direction.UpLeft, Direction.UpRight
            }

        for frog in self.frogs:
            for direction in allowed_directions:
                dest = apply_direction(frog, direction)
                if dest in self.lily_pads and dest not in self.frogs and dest not in self.opponent_frogs:
                    possible_moves.append(MoveAction(frog, [direction]))

        if possible_moves:
            # print_board(self.red_frogs, self.blue_frogs, self.lily_pads)
            return random.choice(possible_moves)
        else:
            # Fallback to GROW if no legal MOVE
            return GrowAction()

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        if isinstance(action, MoveAction):
            # Reconstruct the destination from the start and directions
            current = action.coord  # ✅ use 'coord' instead of 'start'
            for direction in action.directions:
                dr, dc = direction.value
                current = Coord(current.r + dr, current.c + dc)
            destination = current

            self.lily_pads.discard(action.coord)
            # self.lily_pads.add(destination)

            # Update frog positions based on which player moved
            if color == PlayerColor.RED:
                self.red_frogs.discard(action.coord) 
                self.red_frogs.add(destination)
            else:  # PlayerColor.BLUE
                self.blue_frogs.discard(action.coord)
                self.blue_frogs.add(destination)

        elif isinstance(action, GrowAction):
            # Determine which frogs are growing
            frogs = self.red_frogs if color == PlayerColor.RED else self.blue_frogs
            for frog in frogs:
                for adj in adjacent_coords(frog):
                    if adj not in self.lily_pads:
                        self.lily_pads.add(adj)        
        
        self.frogs = self.red_frogs if self._color == PlayerColor.RED else self.blue_frogs
        self.opponent_frogs = self.blue_frogs if self._color == PlayerColor.RED else self.red_frogs    

def adjacent_coords(coord: Coord) -> list[Coord]:
    directions = [
        (-1, -1), (-1, 0), (-1, 1),
        ( 0, -1),          ( 0, 1),
        ( 1, -1), ( 1, 0), ( 1, 1)
    ]
    result = [] 
    for dr, dc in directions: 
        nr, nc = coord.r + dr, coord.c + dc
        if 0 <= nr < 7 and 0 <= nc < 7:
            result.append(Coord(nr, nc))
    return result

def apply_direction(coord: Coord, direction: Direction) -> Coord | None:
    dr, dc = direction.value
    new_r, new_c = coord.r + dr, coord.c + dc
    if 0 <= new_r < 8 and 0 <= new_c < 8:
        return Coord(new_r, new_c)
    return None

def print_board(red_frogs, blue_frogs, lily_pads):
    """
    Print the 8x8 board using:
    - 'R' for red frogs
    - 'B' for blue frogs
    - '*' for lily pads
    - '.' for empty cells
    """
    board = [["." for _ in range(8)] for _ in range(8)]

    for coord in lily_pads:
        board[coord.r][coord.c] = "*"
    for coord in red_frogs:
        board[coord.r][coord.c] = "R"
    for coord in blue_frogs:
        board[coord.r][coord.c] = "B"

    print("\nBoard State:")
    for row in board:
        print(" ".join(row))
    print()