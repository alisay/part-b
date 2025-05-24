# COMP30024 Artificial Intelligence, Semester 1 2025
# Project Part B: Game Playing Agent (Hybrid Minimax + MCTS Rollouts)

from referee.game import PlayerColor, Coord, Direction, Action, MoveAction, GrowAction
import random, copy

# --- Helper Functions ---

def apply_direction(coord: Coord, direction: Direction) -> Coord | None:
    dr, dc = direction.value
    nr, nc = coord.r + dr, coord.c + dc
    if 0 <= nr < 8 and 0 <= nc < 8:
        return Coord(nr, nc)
    return None


def adjacent_coords(coord: Coord) -> list[Coord]:
    dirs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    res = []
    for dr, dc in dirs:
        nr, nc = coord.r+dr, coord.c+dc
        if 0 <= nr < 8 and 0 <= nc < 8:
            res.append(Coord(nr,nc))
    return res


def find_jumps(start: Coord, current: Coord, directions: set[Direction],
               frogs: set[Coord], lily_pads: set[Coord], visited: set[Coord], path: list[Direction]) -> list[list[Direction]]:
    all_paths = []
    for d in directions:
        over = apply_direction(current, d)
        dest = apply_direction(over, d) if over else None
        if (dest and over in frogs and dest in lily_pads
            and dest not in frogs and dest not in visited):
            new_path = path + [d]
            new_frogs = (frogs - {current}) | {dest}
            new_lilies = lily_pads - {current}
            ext = find_jumps(start, dest, directions, new_frogs, new_lilies, visited|{dest}, new_path)
            if ext:
                all_paths.extend(ext)
            else:
                all_paths.append(new_path)
    return all_paths


def print_board(red_frogs, blue_frogs, lily_pads):
    board = [['.' for _ in range(8)] for _ in range(8)]
    for c in lily_pads: board[c.r][c.c] = '*'
    for c in red_frogs: board[c.r][c.c] = 'R'
    for c in blue_frogs: board[c.r][c.c] = 'B'
    print("\nBoard State:")
    for row in board:
        print(' '.join(row))
    print()

# --- Minimax αβ Pruning ---

def minimax_alpha_beta(node, alpha, beta, depth=0):
    if node.isLeaf():
        return node.evaluate(), None
    best = None
    if node.isMax:
        for child in node.children():
            val, _ = minimax_alpha_beta(child, alpha, beta, depth+1)
            if val >= beta:
                return val, None
            if val > alpha:
                alpha, best = val, child.name
        return alpha, best
    else:
        for child in node.children():
            val, _ = minimax_alpha_beta(child, alpha, beta, depth+1)
            if val <= alpha:
                return val, None
            if val < beta:
                beta, best = val, child.name
        return beta, best

# --- GameStateNode for Search ---

class GameStateNode:
    def __init__(self, red_frogs, blue_frogs, lily_pads,
                 isMax, color, name=None, depth=0, max_depth=2):
        self.red_frogs = set(red_frogs)
        self.blue_frogs = set(blue_frogs)
        self.lily_pads = set(lily_pads)
        self.isMax = isMax
        self.color = color
        self.name = name        # Action that led here
        self.depth = depth
        self.max_depth = max_depth

    def isLeaf(self):
        return self.depth >= self.max_depth

    def evaluate(self):
        # Simple heuristic: forward progress diff
        rp = sum(f.r for f in self.red_frogs)
        bp = sum(7 - f.r for f in self.blue_frogs)
        return (rp - bp) if self.color==PlayerColor.RED else (bp - rp)

    def children(self):
        active = self.color if self.isMax else (
            PlayerColor.BLUE if self.color==PlayerColor.RED else PlayerColor.RED)
        frogs = self.red_frogs if active==PlayerColor.RED else self.blue_frogs
        opponent_set = self.blue_frogs if active==PlayerColor.RED else self.red_frogs
        dirs = {Direction.Right, Direction.Left}
        dirs |= ({Direction.Down, Direction.DownLeft, Direction.DownRight}
                 if active==PlayerColor.RED else
                 {Direction.Up, Direction.UpLeft, Direction.UpRight})
        all_frogs = self.red_frogs | self.blue_frogs

        children = []
        # step moves
        for f in frogs:
            for d in dirs:
                dest = apply_direction(f, d)
                if dest and dest in self.lily_pads and dest not in all_frogs:
                    act = MoveAction(f, [d])
                    nr, nb, nl = set(self.red_frogs), set(self.blue_frogs), set(self.lily_pads)
                    nl.discard(f)
                    if active==PlayerColor.RED:
                        nr.discard(f); nr.add(dest)
                    else:
                        nb.discard(f); nb.add(dest)
                    children.append(GameStateNode(nr, nb, nl, not self.isMax,
                                  self.color, name=act, depth=self.depth+1, max_depth=self.max_depth))
        # jumps
        for f in frogs:
            for path in find_jumps(f, f, dirs, all_frogs, self.lily_pads, {f}, []):
                curr = f
                for d in path:
                    curr = apply_direction(apply_direction(curr,d), d)
                act = MoveAction(f, path)
                nr, nb, nl = set(self.red_frogs), set(self.blue_frogs), set(self.lily_pads)
                nl.discard(f)
                if active==PlayerColor.RED:
                    nr.discard(f); nr.add(curr)
                else:
                    nb.discard(f); nb.add(curr)
                children.append(GameStateNode(nr, nb, nl, not self.isMax,
                              self.color, name=act, depth=self.depth+1, max_depth=self.max_depth))
        # grow
        act = GrowAction()
        nr, nb, nl = set(self.red_frogs), set(self.blue_frogs), set(self.lily_pads)
        grow_set = nr if active==PlayerColor.RED else nb
        for frog in grow_set:
            for adj in adjacent_coords(frog): nl.add(adj)
        children.append(GameStateNode(nr, nb, nl, not self.isMax,
                          self.color, name=act, depth=self.depth+1, max_depth=self.max_depth))
        return children

# --- Hybrid Agent: Minimax + MCTS Rollouts ---

class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        # initial state
        self.red_frogs  = {Coord(0,i) for i in range(1,7)}
        self.blue_frogs = {Coord(7,i) for i in range(1,7)}
        self.lily_pads  = {Coord(0,0), Coord(0,7), *{Coord(1,c) for c in range(1,7)},
                           *{Coord(6,c) for c in range(1,7)}, Coord(7,0), Coord(7,7)}

    def action(self, **referee: dict) -> Action:
        print_board(self.red_frogs, self.blue_frogs, self.lily_pads)
        # 1) Root minimax to depth 2
        root = GameStateNode(self.red_frogs, self.blue_frogs, self.lily_pads,
                              isMax=True, color=self._color, max_depth=2)
        scored = []
        for child in root.children():
            val, _ = minimax_alpha_beta(child, float('-inf'), float('inf'))
            scored.append((val, child.name, child))
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = scored[:4]  # top-4

        # 2) Playouts
        def playout_winner(rf, bf, lp, start_color):
            rf, bf, lp = set(rf), set(bf), set(lp)
            turn = start_color
            for _ in range(20):  # playout depth
                # generate moves
                moves = []
                # step & jump as before
                dirs = {Direction.Right, Direction.Left}
                dirs |= ({Direction.Down,Direction.DownLeft,Direction.DownRight}
                         if turn==PlayerColor.RED else
                         {Direction.Up,Direction.UpLeft,Direction.UpRight})
                frogs = rf if turn==PlayerColor.RED else bf
                all_f = rf|bf
                for f in frogs:
                    # steps
                    for d in dirs:
                        dest = apply_direction(f,d)
                        if dest and dest in lp and dest not in all_f:
                            moves.append(MoveAction(f,[d]))
                    # jumps
                    for path in find_jumps(f,f,dirs,all_f,lp,{f},[]):
                        moves.append(MoveAction(f,path))
                # grow
                moves.append(GrowAction())
                if not moves:
                    break
                # choose random-greedy
                if random.random() < 0.2:
                    # greedy by one-ply eval
                    best_m=None; best_s=-float('inf')
                    for m in moves:
                        # apply m to state copy
                        trf, tbf, tlp = set(rf), set(bf), set(lp)
                        self._apply_action(trf, tbf, tlp, turn, m)
                        node = GameStateNode(trf, tbf, tlp, True, self._color, max_depth=0)
                        s = node.evaluate()
                        if s>best_s: best_s, best_m = s, m
                    move = best_m
                else:
                    move = random.choice(moves)
                # apply
                self._apply_action(rf, bf, lp, turn, move)
                # check win
                if any(f.r==7 for f in rf): return PlayerColor.RED
                if any(f.r==0 for f in bf): return PlayerColor.BLUE
                turn = PlayerColor.BLUE if turn==PlayerColor.RED else PlayerColor.RED
            # no terminal: eval
            final = GameStateNode(rf, bf, lp, True, self._color, max_depth=0)
            return self._color if final.evaluate()>0 else (
                   PlayerColor.BLUE if self._color==PlayerColor.RED else PlayerColor.RED)

        # helper to apply move
        def apply_local(trf, tbf, tlp, player, act):
            if isinstance(act, MoveAction):
                cur = act.coord
                tlp.discard(cur)
                for d in act.directions:
                    over = apply_direction(cur, d)
                    cur = apply_direction(over, d) if over in (trf|tbf) else apply_direction(cur,d)
                if player==PlayerColor.RED:
                    trf.discard(act.coord); trf.add(cur)
                else:
                    tbf.discard(act.coord); tbf.add(cur)
            else:
                frogs = trf if player==PlayerColor.RED else tbf
                for f in frogs:
                    for adj in adjacent_coords(f): tlp.add(adj)
        # bind
        self._apply_action = apply_local

        # simulate
        best_move=None; best_rate=-1
        for _, move, child in candidates:
            wins=0
            for _ in range(20):  # playouts per candidate
                winner = playout_winner(child.red_frogs, child.blue_frogs,
                                         child.lily_pads,
                                         PlayerColor.BLUE if self._color==PlayerColor.RED else PlayerColor.RED)
                if winner==self._color: wins+=1
            rate = wins/20
            if rate>best_rate: best_rate, best_move = rate, move

        return best_move

    def update(self, color: PlayerColor, action: Action, **referee: dict):
        # same update logic from original agent
        if isinstance(action, MoveAction):
            cur = action.coord
            for d in action.directions:
                over = apply_direction(cur, d)
                cur = apply_direction(over, d) if over and over in (self.red_frogs|self.blue_frogs) else apply_direction(cur,d)
            dest = cur
            self.lily_pads.discard(action.coord)
            if color==PlayerColor.RED:
                self.red_frogs.discard(action.coord); self.red_frogs.add(dest)
            else:
                self.blue_frogs.discard(action.coord); self.blue_frogs.add(dest)
        else:
            frogs = self.red_frogs if color==PlayerColor.RED else self.blue_frogs
            for f in frogs:
                for adj in adjacent_coords(f): self.lily_pads.add(adj)
        # keep sets consistent
        # no need to reset self._color

# END OF AGENT
