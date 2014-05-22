'''
Created on May 21, 2014

@author: ignacio
'''

import curses
from colors import CursesColors
from chords.library import ChordLibrary
from chords.drawer import draw_chord
import collections


class SubPad():

    def __init__(self, xpos, ypos, width, height):
        self._pad = curses.newpad(1000, 1000)
        self._xpos = xpos
        self._ypos = ypos
        self._width = width
        self._height = height
        self._vertical_scroll = 0

    @property
    def vertical_scroll(self):
        return self._vertical_scroll

    def set_vertical_scroll(self, value):
        if value < 0:
            value = 0
        self._vertical_scroll = value

    def refresh(self):
        self._pad.refresh(self._vertical_scroll, 0,
                          self._ypos, self._xpos,
                          self._ypos + self._height - 1,
                          self._xpos + self._width - 1)

    def clear(self):
        self._pad.clear()

    @property
    def pad(self):
        return self._pad

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height


class MainWindow():

    def __init__(self, curses_screen):
        self._curses_screen = curses_screen
        self._subpads = []
        width, height = self._get_screen_dimensions()
        chord_w, chord_h = self._get_chord_pad_dimensions()
        self._lyrics_pad = self._subpad(width - chord_w - 1, height, 0, 0)
        self._chord_pad = self._subpad(chord_w, chord_h, width - chord_w, 0)
        self._instruction_pad = self._subpad(chord_w, height - chord_h - 1,
                                             width - chord_w, chord_h + 1)
        self._draw_borders()

    def _get_screen_dimensions(self):
        height, width = self._curses_screen.getmaxyx()
        return width, height

    def _get_chord_pad_dimensions(self):
        width, height = self._get_screen_dimensions()
        pad_width = min(36, width / 2)
        pad_height = min(15, height / 2)
        return pad_width, pad_height

    def _subpad(self, width, height, xpos, ypos):
        subpad = SubPad(xpos, ypos, width, height)
        self._subpads.append(subpad)
        return subpad

    def _draw_borders(self):
        width, height = self._get_screen_dimensions()
        chord_w, chord_h = self._get_chord_pad_dimensions()
        for ypos in xrange(height):
            xpos = width - chord_w - 1
            self._curses_screen.addstr(ypos, xpos, "x")
        for subxpos in xrange(chord_w):
            ypos = chord_h
            xpos = width - chord_w + subxpos
            self._curses_screen.addstr(ypos, xpos,
                                       "x")

    def refresh(self):
        self._curses_screen.refresh()
        for subpad in self._subpads:
            subpad.refresh()

    @property
    def lyrics_pad(self):
        return self._lyrics_pad

    @property
    def chord_pad(self):
        return self._chord_pad

    @property
    def instruction_pad(self):
        return self._instruction_pad


class CursesRenderer():

    def __init__(self, screen, tab, instrument):
        self._screen = screen
        self._window = MainWindow(screen)
        self._tab = tab
        self._instrument = instrument
        self._chord_library = ChordLibrary(self._instrument)
        self._reverse_chord_draw = False
        self._all_chords = list(self._all_chord_coords())
        self._chord_version = collections.defaultdict(int)
        self._selected_chord_index = 0
        self._selected_chord = None
        self._quit = False

    def run(self):
        while not self._quit:
            self._render()
            self._refresh()
            key = self._screen.getch()
            self._process_key(key)

    def _process_key(self, key):
        if key == ord('n'):
            self._selected_chord_index += 1
            self._center_chord()
        elif key == ord('b'):
            self._selected_chord_index -= 1
            self._center_chord()
        if key == ord('j'):
            self._chord_version[self._selected_chord] += 1
        elif key == ord('h'):
            self._chord_version[self._selected_chord] -= 1
        elif key == ord('q'):
            self._quit = True

    def _center_chord(self):
        subpad = self._window.lyrics_pad
        chord_line = self._all_chords[self._selected_chord_index][0]
        subpad.set_vertical_scroll(chord_line - subpad.height / 2)

    def _render(self):
        self._update_selected_chord()
        self._render_tab()
        self._render_chord()
        # render instructions

    def _update_selected_chord(self):
        try:
            nline, nchord = self._all_chords[self._selected_chord_index]
            line = self._tab.lines[nline]
            self._selected_chord = line.contents().chords[nchord][0]
        except IndexError:
            self._selected_chord = None

    def _all_chord_coords(self):
        for nline, line in enumerate(self._tab.lines):
            for nchord in xrange(len(line.contents().chords)):
                yield nline, nchord

    def _refresh(self):
        self._window.refresh()

    def _render_tab(self):
        self._window.lyrics_pad.clear()
        for ypos, line in enumerate(self._tab.lines):
            self._render_line(line, ypos)

    def _render_line(self, line, ypos):
        contents = line.contents()
        if contents.chords:
            self._render_tab_chords(contents, ypos)
        else:
            self._render_tab_text(contents, ypos)

    def _render_tab_text(self, contents, ypos):
        self._write(self._window.lyrics_pad, 0, ypos, contents.line)

    def _render_tab_chords(self, contents, ypos):
        cursor = 0
        for nchord, (chord, pos) in enumerate(contents.chords):
            cursor = max(cursor, pos)
            text = chord.text()
            attr = curses.A_BOLD
            if (ypos, nchord) == self._all_chords[self._selected_chord_index]:
                attr |= curses.A_STANDOUT
            self._write(self._window.lyrics_pad,
                        cursor, ypos, text,
                        CursesColors.CURSES_CHORD_COLOR,
                        attr)
            cursor += len(text)
            fingering = self._get_fingering(chord)
            if fingering:
                text = "({})".format(fingering)
                self._write(self._window.lyrics_pad,
                            cursor, ypos, text,
                            CursesColors.CURSES_FINGERING_COLOR,
                            attr)
                cursor += len(text)

            cursor += 1

    def _render_chord(self):
        self._window.chord_pad.clear()
        fingering = self._get_fingering(self._selected_chord)
        if fingering:
            chord = self._selected_chord
            lines = draw_chord(fingering, reverse=self._reverse_chord_draw)
            fingerings = self._chord_library.get_all(chord)
            version = self._chord_version[chord] % len(fingerings)

            self._write(self._window.chord_pad, 0, 0,
                        "{} ({})".format(chord, fingering))
            self._write(self._window.chord_pad, 0, 1, "Version {} of {}"
                        .format(version + 1, len(fingerings)))
            for nline, line in enumerate(lines):
                for nchar, char in enumerate(line):
                    if char in ['o', 'x']:
                        color = CursesColors.CURSES_FINGERING_COLOR
                        attr = curses.A_BOLD
                    else:
                        color = CursesColors.CURSES_DEFAULT_COLOR
                        attr = 0
                    self._write(self._window.chord_pad, nchar, 3 + nline, char,
                                color, attr)
        else:
            self._write(self._window.chord_pad, 0, 0,
                        "{} No fingerings :(".format(self._selected_chord))

    def _get_fingering(self, chord):
        fingerings = self._chord_library.get_all(chord)
        if fingerings:
            version = self._chord_version[chord] % len(fingerings)
            return fingerings[version]
        return None

    def _write(self, subpad, xpos, ypos, text, color_id=0, attr=0):
        subpad.pad.addstr(ypos, xpos, text, curses.color_pair(color_id) | attr)
