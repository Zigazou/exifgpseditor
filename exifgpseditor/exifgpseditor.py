#!/usr/bin/env python3
"""An Exif GPS editor

This single Python3 program allows the end user to modify GPS coordinates in
image files. It uses OsmGpsMap and GExiv2 in order to achieve this.
"""

from configparser import ConfigParser
from re import search
from sys import argv
from os.path import expanduser, isfile, join, dirname, abspath
from gi import require_version
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, GExiv2, OsmGpsMap

require_version('Gtk', '3.0')
require_version('GExiv2', '0.10')
require_version('OsmGpsMap', '1.0')

GObject.threads_init()
Gdk.threads_init()
GObject.type_register(OsmGpsMap.Map)

def get_resource(filename):
    """Given a filename, return an absolute path to it in a list of authorized
    directories. It returns None if the file cannot be found in an authorized
    directory.

    The directories searched for are:

    - the directory of this script
    - the current user ~/.share directory
    - the local share directory of the OS /usr/local/share
    - the share directory of the OS /usr/share
    """
    resources = [
        abspath(join(dirname(__file__), filename)),
        expanduser(join("~", ".share", "exifgpseditor", filename)),
        join("/usr/local/share/exifgpseditor", filename),
        join("/usr/share/exifgpseditor", filename)
    ]

    return next((res for res in resources if isfile(res)), None)

def get_config(filename):
    """Returns the absolute path to the config file given its filename. This
    function does not ensure the file does exist.
    """
    return expanduser(join("~", ".config", filename))

class Configuration:
    """The Configuration class is an helper class dedicated to read and
    write configuration file for the ExifGpsEditor.

    At the moment, it gives only the previous_position attribute which
    contains a tuple of (latitude, longitude).
    """
    def __init__(self, filename):
        assert isinstance(filename, str)

        self._filename = get_config(filename)
        self._config = ConfigParser()

        self._config['DEFAULT'] = {
            'latitude': 0,
            'longitude': 0
        }

        self._config['gps'] = {}
        self.previous_position = (0.0, 0.0)

    def load(self):
        """Read the config file and place specific values in attributes."""
        self._config.read(self._filename)

        self.previous_position = (
            float(self._config['gps']['latitude']),
            float(self._config['gps']['longitude'])
        )

    def save(self):
        """Save the config file from specific values in attributes."""
        self._config['gps']['latitude'] = str(self.previous_position[0])
        self._config['gps']['longitude'] = str(self.previous_position[1])

        with open(self._filename, 'w') as configfile:
            self._config.write(configfile)

def gps_str2float(value):
    """Convert a coordinate (either latitude or longitude) in the Exiv2 format
    to a floating point value suited for OsmGpsMap.

    The coordinate is a string looking like "49/1 50/1 23546/6000"
    """
    assert isinstance(value, str)

    dms = search(r'^(\d+)/(\d+) (\d+)/(\d+) (\d+)/(\d+)$', value)

    try:
        (vdg, ddg, vmi, dmi, vse, dse) = dms.group(1, 2, 3, 4, 5, 6)
        degree = float(vdg) / float(ddg)
        minute = float(vmi) / float(dmi)
        second = float(vse) / float(dse)

        return degree + (minute / 60) + (second / 3600)
    except (AttributeError, ZeroDivisionError):
        return 0.0

def gps_float2str(value):
    """Convert a coordinate (either latitude or longitude) from OsmGpsMap
    floating point format to the Exiv2 format.

    The coordinate is a float.
    """
    assert isinstance(value, float)

    degree = int(value)
    minute = int(value * 60) % 60
    second = int(abs(value) * 3600 * 6000) % (60 * 6000)

    return "%d/1 %d/1 %d/6000" % (degree, minute, second)

class ExifGpsEditor:
    """Operate a GUI displaying an OpenStreetMap map and an image preview, and
    let the user modify the GPS coordinates.
    """
    def __init__(self, config):
        assert isinstance(config, Configuration)

        self.meta = None
        self.original_position = (0, 0)
        self.config = config

        # Set the Glade file
        builder = Gtk.Builder()
        builder.add_from_file(get_resource("exifgpseditor.glade"))

        handlers = {
            "quit": (lambda _: Gtk.main_quit()),
            "apply": (lambda _: self.save_image()),
            "redraw": (lambda _: self.move_to(None)),
            "origin": (lambda _: self.move_to(self.original_position)),
            "previous": (lambda _: self.move_to(self.config.previous_position))
        }
        builder.connect_signals(handlers)

        # Get the Main Window, and connect the "destroy" event
        self.win_exifgpseditor = builder.get_object("win_exifgpseditor")
        self.win_exifgpseditor.connect('destroy', lambda x: Gtk.main_quit())

        # Add zoom buttons and target to the map
        self.themap = builder.get_object("map_gps")
        self.themap.layer_add(
            OsmGpsMap.MapOsd(
                show_zoom=True,
                show_crosshair=True
            )
        )

        # Get the image widget
        self.img_preview = builder.get_object("img_preview")

        self.win_exifgpseditor.show_all()

    def move_to(self, position):
        """Change the center of the map to a position (a tuple of 2 float). If
        None is passed, it centers on the coordinates of the map (useful
        because OsmGpsMap does not center correctly when resizing the window).
        """
        if position is None:
            lat = self.themap.props.latitude
            lon = self.themap.props.longitude
        else:
            (lat, lon) = position

        self.themap.set_center(lat, lon)

    def load_image(self, filename):
        """Load an image. It generates a thumbnail and retrieve its GPS
        coordinates.
        """
        self.meta = GExiv2.Metadata(filename)

        try:
            self.original_position = (
                gps_str2float(self.meta['Exif.GPSInfo.GPSLatitude']),
                gps_str2float(self.meta['Exif.GPSInfo.GPSLongitude'])
            )
        except KeyError:
            self.original_position = (0.0, 0.0)

        self.move_to(self.original_position)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 160, 100)
        self.img_preview.set_from_pixbuf(pixbuf)

    def save_image(self):
        """Save an image with the current GPS coordinates given by the user."""
        (lat, lon) = (self.themap.props.latitude, self.themap.props.longitude)

        self.meta['Exif.GPSInfo.GPSLatitude'] = gps_float2str(lat)
        self.meta['Exif.GPSInfo.GPSLongitude'] = gps_float2str(lon)

        self.meta.save_file()

        self.config.previous_position = (lat, lon)

def exit_with_error(message, return_code):
    """Display an alert box with a message and exit the application with an
    error code which must be different from zero.
    """
    assert isinstance(return_code, int) and return_code > 0

    Gtk.MessageDialog(
        Gtk.Window(),
        Gtk.DialogFlags.DESTROY_WITH_PARENT,
        Gtk.MessageType.INFO,
        Gtk.ButtonsType.CLOSE,
        message
    ).run()

    exit(return_code)

def run():
    """The main function."""
    if len(argv) < 2:
        exit_with_error("No file!", 1)

    if not isfile(argv[1]):
        exit_with_error("File not found", 2)

    config = Configuration('exifgpseditor.ini')
    config.load()

    exif_gps_editor = ExifGpsEditor(config)
    exif_gps_editor.load_image(argv[1])

    Gtk.main()

    config.save()

if __name__ == '__main__':
    run()
