#!/usr/bin/env python3

from gi import require_version
require_version('Gtk', '3.0')
require_version('GExiv2', '0.10')
require_version('OsmGpsMap', '1.0')

from configparser import ConfigParser
from gi.repository import Gtk, Gdk, GdkPixbuf, GObject, GExiv2, OsmGpsMap
from re import search
from sys import argv
from os.path import expanduser, isfile, join, dirname, abspath

GObject.threads_init()
Gdk.threads_init()
GObject.type_register(OsmGpsMap.Map)

def get_resource(filename):
    resources = [
        join(abspath(dirname(__file__)), filename),
        join(expanduser("~"), ".share", "exifgpseditor", filename),
        join("/usr/local/share/exifgpseditor", filename),
        join("/usr/share/exifgpseditor", filename)
    ]

    return next((res for res in resources if isfile(res)), None)

def get_config(filename):
    return join(expanduser("~"), "/.config/", filename)

class Configuration:
    def __init__(self, filename):
        assert isinstance(filename, str)

        self._filename = get_config(filename)
        self._config = ConfigParser()

        self._config['DEFAULT'] = {
            'latitude': 0,
            'longitude': 0
        }

        self._config['gps'] = {}

    def load(self):
        self._config.read(self._filename)

        self.previous_position = (
            float(self._config['gps']['latitude']),
            float(self._config['gps']['longitude'])
        )

    def save(self):
        self._config['gps']['latitude'] = str(self.previous_position[0])
        self._config['gps']['longitude'] = str(self.previous_position[1])

        with open(self._filename, 'w') as configfile:
            self._config.write(configfile)

def gps_str2float(value):
    assert isinstance(value, str)

    dms = search(r'^(\d+)/(\d+) (\d+)/(\d+) (\d+)/(\d+)$', value)

    try:    
        (vd, dd, vm, dm, vs, ds) = dms.group(1, 2, 3, 4, 5, 6)
        d = float(vd) / float(dd)
        m = float(vm) / float(dm)
        s = float(vs) / float(ds)

        return d + (m / 60) + (s / 3600)
    except:
        return 0.0

def gps_float2str(value):
    assert isinstance(value, float)

    d = int(value)
    m = int(value * 60) % 60
    s = int(abs(value) * 3600 * 6000) % (60 * 6000)

    return "%d/1 %d/1 %d/6000" % (d, m, s)

class ExifGpsEditor:
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
        if position is None:
            lat = self.themap.props.latitude
            lon = self.themap.props.longitude
        else:
            (lat, lon) = position

        self.themap.set_center(lat, lon)

    def load_image(self, filename):
        self.meta = GExiv2.Metadata(filename)

        self.original_position = (
            gps_str2float(self.meta['Exif.GPSInfo.GPSLatitude']),
            gps_str2float(self.meta['Exif.GPSInfo.GPSLongitude'])
        )

        self.move_to(self.original_position)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 160, 100)
        self.img_preview.set_from_pixbuf(pixbuf)

    def save_image(self):
        (lat, lon) = (self.themap.props.latitude, self.themap.props.longitude)

        self.meta['Exif.GPSInfo.GPSLatitude'] = gps_float2str(lat)
        self.meta['Exif.GPSInfo.GPSLongitude'] = gps_float2str(lon)

        self.meta.save_file()

        self.config.previous_position = (lat, lon)

def exit_with_error(message, rc):
    Gtk.MessageDialog(
        Gtk.Window(),
        Gtk.DialogFlags.DESTROY_WITH_PARENT,
        Gtk.MessageType.INFO,
        Gtk.ButtonsType.CLOSE,
        message
    ).run()

    exit(rc)

def run():
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

if __name__ == '__main__' :
    run()
