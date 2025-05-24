# COMP30024 Artificial Intelligence, Semester 1 2025
# Project Part B: Game Playing Agent (Hybrid Minimax + MCTS Rollouts + Time Management)

from referee.game import PlayerColor, Coord, Direction, Action, MoveAction, GrowAction
import random, copy, time

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
            all_paths.extend(ext if ext else [new_path])
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
        rp = sum(f.r for f in self.red_frogs)
        bp = sum(7 - f.r for f in self.blue_frogs)
        return (rp - bp) if self.color==PlayerColor.RED else (bp - rp)

    def children(self):
        active = self.color if self.isMax else (
            PlayerColor.BLUE if self.color==PlayerColor.RED else PlayerColor.RED)
        frogs = self.red_frogs if active==PlayerColor.RED else self.blue_frogs
        dirs = {Direction.Right, Direction.Left}
        dirs |= ({Direction.Down,Direction.DownLeft,Direction.DownRight}
                 if active==PlayerColor.RED else {Direction.Up,Direction.UpLeft,Direction.UpRight})
        all_frogs = self.red_frogs | self.blue_frogs

        children = []
        for f in frogs:
            # step
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
                    children.append(GameStateNode(nr,nb,nl,not self.isMax,self.color,act,self.depth+1,self.max_depth))
            # jumps
            for path in find_jumps(f,f,dirs,all_frogs,self.lily_pads,{f},[]):
                curr=f
                for d in path:
                    curr=apply_direction(apply_direction(curr,d),d)
                act=MoveAction(f,path)
                nr, nb, nl = set(self.red_frogs), set(self.blue_frogs), set(self.lily_pads)
                nl.discard(f)
                if active==PlayerColor.RED:
                    nr.discard(f); nr.add(curr)
                else:
                    nb.discard(f); nb.add(curr)
                children.append(GameStateNode(nr,nb,nl,not self.isMax,self.color,act,self.depth+1,self.max_depth))
        # grow
        act=GrowAction()
        nr, nb, nl = set(self.red_frogs), set(self.blue_frogs), set(self.lily_pads)
        grow_set = nr if active==PlayerColor.RED else nb
        for frog in grow_set:
            for adj in adjacent_coords(frog): nl.add(adj)
        children.append(GameStateNode(nr,nb,nl,not self.isMax,self.color,act,self.depth+1,self.max_depth))
        return children

# --- Hybrid Agent: Minimax + MCTS Rollouts + Time Management ---

class Agent:
    def __init__(self, color: PlayerColor, **referee: dict):
        self._color = color
        self.red_frogs  = {Coord(0,i) for i in range(1,7)}
        self.blue_frogs = {Coord(7,i) for i in range(1,7)}
        self.lily_pads  = {Coord(0,0),Coord(0,7),*{Coord(1,c) for c in range(1,7)},*{Coord(6,c) for c in range(1,7)},Coord(7,0),Coord(7,7)}
        # time tracking
        self.cpu_time_used = 0.0  # accumulated CPU seconds
        self.max_cpu_time = 180.0
        self.max_wall_time = 180.0

    def action(self, **referee: dict) -> Action:
        # check CPU budget
        if self.cpu_time_used >= self.max_cpu_time:
            return GrowAction()  # out of time, safe action
        # start timers
        start_cpu = time.process_time()
        start_wall = time.time()

        print_board(self.red_frogs, self.blue_frogs, self.lily_pads)
        # 1) Root minimax to depth 2
        root = GameStateNode(self.red_frogs, self.blue_frogs, self.lily_pads,
                              True, self._color, max_depth=2)
        scored = []
        for child in root.children():
            # wall-clock check
            if time.time() - start_wall > self.max_wall_time:
                break
            val, _ = minimax_alpha_beta(child, float('-inf'), float('inf'))
            scored.append((val, child.name, child))
        scored.sort(key=lambda x: x[0], reverse=True)
        candidates = [s for s in scored[:4]]

        # helper to apply moves in playout
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

        # 2) Playouts
        best_move = GrowAction()
        best_rate = -1.0
        for _, move, child in candidates:
            if time.time() - start_wall > self.max_wall_time:
                break
            wins = 0
            for _ in range(20):
                if time.time() - start_wall > self.max_wall_time:
                    break
                # simulate playout
                rf, bf, lp = set(child.red_frogs), set(child.blue_frogs), set(child.lily_pads)
                turn = PlayerColor.BLUE if self._color==PlayerColor.RED else PlayerColor.RED
                for _ in range(20):
                    # generate moves (steps, jumps, grow)
                    moves = []
                    dirs = {Direction.Right, Direction.Left}
                    dirs |= ({Direction.Down,Direction.DownLeft,Direction.DownRight} if turn==PlayerColor.RED else {Direction.Up,Direction.UpLeft,Direction.UpRight})
                    frogs = rf if turn==PlayerColor.RED else bf
                    all_f = rf|bf
                    for f in frogs:
                        for d in dirs:
                            dest = apply_direction(f, d)
                            if dest and dest in lp and dest not in all_f:
                                moves.append(MoveAction(f,[d]))
                        for p in find_jumps(f,f,dirs,all_f,lp,{f},[]):
                            moves.append(MoveAction(f,p))
                    moves.append(GrowAction())
                    if not moves: break
                    act = random.choice(moves)
                    apply_local(rf, bf, lp, turn, act)
                    if any(f.r==7 for f in rf):
                        if self._color==PlayerColor.RED: wins+=1
                        break
                    if any(f.r==0 for f in bf):
                        if self._color==PlayerColor.BLUE: wins+=1
                        break
                    turn = PlayerColor.BLUE if turn==PlayerColor.RED else PlayerColor.RED
            rate = wins/20 if wins else 0
            if rate > best_rate:
                best_rate, best_move = rate, move

        # end timers
        used_cpu = time.process_time() - start_cpu
        self.cpu_time_used += used_cpu
        return best_move

    def update(self, color: PlayerColor, action: Action, **referee: dict):
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
