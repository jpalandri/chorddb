'''
Created on May 10, 2014

@author: ignacio
'''
from chords import CHORD_RE, Chord, ChordLibrary
import StringIO
import colors
import logging
import re

LOGGER = logging.getLogger(__name__)


class Tablature():

    def __init__(self, lines):
        self._lines = lines

    def render(self, debug=False, instrument=None):
        res = StringIO.StringIO()
        for line in self._lines:
            print >> res, line.render(debug=debug, instrument=instrument)
        return res.getvalue()

    @classmethod
    def parse(cls, lines):
        return cls([TablatureLine.from_line(l.rstrip("\n")) for l in lines])


class TablatureLine():

    def render(self, debug=False, instrument=None):
        contents = []
        if debug:
            contents.append(colors.ColoredOutput.colored(
                "{}:".format(self.__class__.__name__),
                fore=colors.Fore.GREEN, style=colors.Style.BRIGHT
            ))
        contents.append(self._render(instrument=instrument))
        return "".join(contents)

    def _render(self, **kwargs):
        raise NotImplementedError()

    @classmethod
    def from_line(cls, line):
        return cls._autodetect_line_class(line).from_line(line)

    @staticmethod
    def _autodetect_line_class(line):
        stripped = line.strip()
        if not stripped:
            return EmptyLine
        remainder = re.sub("\s+", " ", re.sub(CHORD_RE, "", stripped))
        if len(remainder) * 2 < len(re.sub("\s+", " ", stripped)):
            return ChordLine
        return LyricLine


class ChordLine(TablatureLine):

    def __init__(self, chords, positions):
        self._chords = chords
        self._positions = positions

    def _render(self, instrument=None, **kwargs):
        if len(self._positions) < len(self._chords):
            self._positions += [-1] * \
                (len(self._chords) - len(self._positions))
        buff = colors.ColoredOutput(fore=colors.Fore.CYAN)
        for pos, chord in zip(self._positions, self._chords):
            if buff.tell() < pos:
                buff.write(" " * (pos - buff.tell()))
            buff.write(chord.text(), style=colors.Style.BRIGHT)
            try:
                c = ChordLibrary.get(chord, instrument)
            except ValueError:
                LOGGER.warning("Could not find %s in ChordLibrary for "
                               "'%s'", chord, instrument)
                c = None
            if c:
                buff.write("({})".format(c), fore=colors.Fore.RED)
            buff.write(" ")
        return buff.getvalue().rstrip()

    @classmethod
    def from_line(cls, line):
        chordpos = Chord.extract_chordpos(line)
        chords, positions = (list(x) for x in zip(*chordpos))
        return cls(chords, positions)


class LyricLine(TablatureLine):

    def __init__(self, line):
        self._line = line

    def _render(self, **kwargs):
        return self._line

    @classmethod
    def from_line(cls, line):
        return cls(line)


class EmptyLine(TablatureLine):

    def _render(self, **kwargs):
        return ""

    @classmethod
    def from_line(cls, line):
        return cls()
