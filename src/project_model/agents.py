from mesa import Agent
from .domain import similarity

class TrackAgent(Agent):
    # stores a songs scores and whether it can be recommended:
    def __init__(self, model, track):
        super().__init__(model)
        self.track = track
        self.eligible = track.track_id not in model.excluded
        self.selected_rank = 0  # 0 means the song has not been selected
        self.established_score = similarity(track, model.established, model.scales)
        self.recent_score = similarity(track, model.recent, model.scales)
        
        # combines both profile scores using the recent-listening weight:
        self.score = self.established_score + model.weight * (self.recent_score - self.established_score)
        self.proposed_score = None

    def step(self):
        self.proposed_score = self.score if self.eligible and self.selected_rank == 0 else None #makes the score available for selection if the song is eligible and not already in the playlist


class ListenerAgent(Agent):
    # builds the listeners playlist, one song per step:
    def __init__(self, model):
        super().__init__(model)
        self.playlist = []
        self.last_selected = ""

    def step(self):
        candidates = [song for song in self.model.tracks if song.proposed_score is not None]
        if not candidates:
            raise RuntimeError("Not enough eligible tracks")
        
        # takes the highest score, with the lowest song ID first if scores are equal:
        chosen = min(candidates, key=lambda song: (-song.proposed_score, song.track.track_id))
        self.playlist.append(chosen.track.track_id)
        self.last_selected = chosen.track.track_id
        chosen.selected_rank = len(self.playlist)
        chosen.proposed_score = None

