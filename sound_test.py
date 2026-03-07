import pyxel


RESOURCE_FILE = "sounds.pyxres"
MELODY_BASS_TRACK_ID = 0
DRUM_TRACK_ID = 2


class App:
    def __init__(self):
        pyxel.init(200, 150, title="Pyxel Sound API")
        pyxel.load(RESOURCE_FILE, excl_images=True, excl_tilemaps=True)
        self.melody_bass_channels = self._read_track_channels(MELODY_BASS_TRACK_ID)

        pyxel.images[0].set(
            0,
            0,
            [
                "00011000",
                "00010100",
                "00010010",
                "00010010",
                "00010100",
                "00010000",
                "01110000",
                "01100000",
            ],
        )

        self.play_music(True, True, True)
        pyxel.run(self.update, self.draw)

    def _read_track_channels(self, track_id):
        music = pyxel.musics[track_id]

        # Pyxel music channel fields may differ by version; try common layouts.
        def read_channel(channel):
            for attr_name in (f"seq{channel}", f"ch{channel}"):
                seq = getattr(music, attr_name, None)
                if seq is not None:
                    return list(seq)

            seqs = getattr(music, "seqs", None)
            if seqs is not None and channel < len(seqs):
                return list(seqs[channel])

            try:
                return list(music[channel])
            except Exception:
                return []

        return tuple(read_channel(i) for i in range(4))

    def play_music(self, ch0, ch1, ch2):
        pyxel.stop()

        if ch0 and self.melody_bass_channels[0]:
            pyxel.play(0, self.melody_bass_channels[0], loop=True)

        if ch1 and self.melody_bass_channels[1]:
            pyxel.play(1, self.melody_bass_channels[1], loop=True)

        if ch2:
            pyxel.playm(DRUM_TRACK_ID, loop=True)

    def update(self):
        if pyxel.btnp(pyxel.KEY_Q):
            pyxel.quit()

        if pyxel.btnp(pyxel.KEY_1):
            self.play_music(True, True, True)
        if pyxel.btnp(pyxel.KEY_2):
            self.play_music(True, False, False)
        if pyxel.btnp(pyxel.KEY_3):
            self.play_music(False, True, False)
        if pyxel.btnp(pyxel.KEY_4):
            self.play_music(False, False, True)
        if pyxel.btnp(pyxel.KEY_5):
            self.play_music(False, False, False)

    def draw(self):
        pyxel.cls(1)

        pyxel.text(6, 6, "sounds loaded from sounds.pyxres", 7)
        pyxel.rect(12, 14, 177, 35, 2)
        pyxel.text(16, 17, "note  :[CDEFGAB] + [ #-] + [0-4] or [R]", 9)
        pyxel.text(16, 25, "tone  :[T]riangle [S]quare [P]ulse [N]oise", 9)
        pyxel.text(16, 33, "volume:[0-7]", 9)
        pyxel.text(16, 41, "effect:[N]one [S]lide [V]ibrato [F]adeOut", 9)

        pyxel.text(6, 53, "musics[msc].set(seq0,seq1,seq2,...)", 7)
        pyxel.text(6, 62, "play(ch,snd,[loop],[resume])", 7)
        pyxel.text(6, 71, "playm(msc,[loop])", 7)
        pyxel.text(6, 80, "stop([ch])", 7)

        pyxel.rectb(6, 97, 188, 47, 14)
        pyxel.rect(6, 91, 29, 7, 14)
        pyxel.text(7, 92, "CONTROL", 1)

        pyxel.text(12, 102, "1: Play melody+bass (track 0) + drums", 14)
        pyxel.text(12, 110, "2: Play melody (track 0 ch0)", 14)
        pyxel.text(12, 118, "3: Play bass (track 0 ch1)", 14)
        pyxel.text(12, 126, "4: Play drums (track 2)", 14)
        pyxel.text(12, 134, "5: Stop playing", 14)

        pyxel.text(137, 107, "play_pos(ch)", 15)

        for i in range(3):
            x = 140 + i * 16
            y = 123 + pyxel.sin(pyxel.frame_count * 5.73 + i * 120.3) * 5
            col = 15 if pyxel.play_pos(i) else 13
            pyxel.pal(1, col)
            pyxel.blt(x, y, 0, 0, 0, 8, 8, 0)

        pyxel.pal()


App()
