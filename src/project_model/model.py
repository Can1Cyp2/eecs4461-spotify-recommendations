# selects ten songs for one playlist, adding one song per Mesa step:
from fractions import Fraction
from mesa import Model
from mesa.datacollection import DataCollector
from .agents import ListenerAgent, TrackAgent
from .domain import make_profile


class RecommendationModel(Model):
    def __init__(self, catalogue, profiles, scales, scenario, weight, playlist_size=10, seed=4461):
        # checks the settings and creates the song agents and listener:
        super().__init__(seed=seed)
        self.weight = Fraction(str(weight))
        if not 0 <= self.weight <= 1:
            raise ValueError("weight must be finite and between 0 and 1")
        if scenario not in profiles["recent"]:
            raise ValueError("Unknown scenario")
        if not isinstance(playlist_size, int) or isinstance(playlist_size, bool) or playlist_size < 1:
            raise ValueError("playlist_size must be a positive integer")
        self.scenario = scenario
        self.scales = scales
        by_id = {t.track_id: t for t in catalogue}
        self.established = make_profile(profiles["established"], by_id, scales)
        self.recent = make_profile(profiles["recent"][scenario], by_id, scales)
        
        # songs from either listening set stay excluded, even when its weight is 0:
        self.excluded = set(self.established.ids) | set(self.recent.ids)
        if len(catalogue) - len(self.excluded) < playlist_size:
            raise ValueError("Playlist exceeds eligible pool")
        self.playlist_size = playlist_size
        self.tracks = [TrackAgent(self, t) for t in catalogue]
        self.listener = ListenerAgent(self)

        # records the playlist and agent states before selection and after each step:
        self.datacollector = DataCollector(
            model_reporters={
                "scenario": "scenario",
                "weight": lambda m: float(m.weight),
                "selected_count": lambda m: len(m.listener.playlist),
                "last_selected": lambda m: m.listener.last_selected,
                "playlist_ids": lambda m: "|".join(m.listener.playlist),
            },
            agent_reporters={
                "kind": lambda a: "track" if isinstance(a, TrackAgent) else "listener",
                "track_id": lambda a: a.track.track_id if isinstance(a, TrackAgent) else "",
                "eligible": lambda a: int(a.eligible) if isinstance(a, TrackAgent) else "",
                "selected_rank": lambda a: a.selected_rank if isinstance(a, TrackAgent) else "",
                "score": lambda a: float(a.score) if isinstance(a, TrackAgent) else "",
                "playlist_length": lambda a: len(a.playlist) if isinstance(a, ListenerAgent) else "",
            },
        )
        self.datacollector.collect(self)

    def step(self):
        if not self.running:
            return
        # all songs make their scores available, then the listener picks one:
        self.agents_by_type[TrackAgent].do("step")
        self.listener.step()
        self.running = len(self.listener.playlist) < self.playlist_size
        self.datacollector.collect(self)

    def run(self):
        # repeats the selection until the ten song playlist is full:
        while self.running:
            self.step()
        return tuple(self.listener.playlist)

    def ranking(self):
        # returns all eligible songs from highest to lowest score, using song ID for ties:
        return sorted((song for song in self.tracks if song.eligible),
                      key=lambda song: (-song.score, song.track.track_id))

