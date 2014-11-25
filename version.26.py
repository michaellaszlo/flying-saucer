import simplegui
import random, math

CANVAS_WIDTH = 480
CANVAS_HEIGHT = 270
PLANET_WIDTH = 1920
PLANET_HEIGHT = 500
GRAVITY = -1.1/60.0
FRICTION = 0.15
BOOST = 25/60.0
sprite_sheet = simplegui.load_image(
        'http://dl.dropbox.com/s/x34dwxqbck3flxd/sprites.g.png')

class Planet:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.generate_terrain()
        
    def generate_terrain(self):
        '''Makes a polyline that starts and stops at the
        same height to produce a wraparound effect. Also stores the
        flat sections as a convenience for creature generation.'''
        length = self.width
        # A segment is a flat section followed by a hill.
        min_segment, max_segment = length//25, length//10
        min_height, max_height = self.height//15, self.height//5
        # Start by calculating segment lengths. Make points later.
        flats = []
        pos = 0
        while True:
            if length-pos < min_segment:
                # Stretch the segments to make them fit the planet.
                scale = 1.0*length/pos
                for flat in flats:
                    flat[0] = int(scale*flat[0])
                    flat[1] = int(scale*flat[1])
                break
            segment = random.randrange(min_segment, max_segment+1)
            # Prevent the final segment from overflowing.
            if pos+segment > length:
                segment = length-pos
            # The split is uniformly distributed between fixed limits.
            width = random.randrange(segment//5, 4*segment//5 + 1)
            # Assign a height now so that hills can refer to it.
            height = random.randrange(min_height, max_height+1)
            flats.append([pos, pos+width, height])
            pos += segment
        # Add a dummy flat to ease the insertion of hills.
        flats.append([length, length, flats[0][2]])
        self.points = points = []
        # Make the initial flat.
        points.append((flats[0][0], flats[0][2], None))
        points.append((flats[0][1], flats[0][2], 'flat'))
        for i in range(1, len(flats)):
            x_begin, y_begin = flats[i-1][1], flats[i-1][2]
            x_end, y_end = flats[i][0], flats[i][2]
            low, high = min(y_begin, y_end), max(y_begin, y_end)
            num_peaks = random.randrange(-3, 4)
            if num_peaks < 0:
                num_peaks *= -1
                y_low = low - 3*min_height/2
                y_high = low - min_height/4
            else:
                y_low = high + min_height/4
                y_high = high + 3*min_height/2
            span = x_end - x_begin
            x = x_begin
            # Render the peaks
            for j in range(num_peaks):
                x += int(1.0*span/(num_peaks+1))
                y = random.randrange(y_low, y_high+1)
                points.append((x, y, 'hill'))
            # Make the last piece of the hill.
            points.append((flats[i][0], flats[i][2], 'hill'))
            # Make the flat that follows.
            points.append((flats[i][1], flats[i][2], 'flat'))
        # Discard the dummy flat.
        points.pop()
        for x, y in points:
            print '%d %d' % (x, y)

    def set_frame(self, frame):
        self.frame = frame
        
    def update(self, canvas):
        points = self.points
        for i in range(1, len(points)):
            x0, y0, type0 = points[i-1]
            x1, y1, type1 = points[i]
            if type1 == 'flat':
                color = 'gray'
            else:
                color = 'gray'
            p0 = self.frame.convert(x0, y0)
            p1 = self.frame.convert(x1, y1)
            canvas.draw_line(p0, p1, 2, color)

class Frame:
    def __init__(self, planet, zoom, viewport):
        self.planet = planet
        self.zoom = zoom
        self.viewport = viewport
        self.width = planet.width/zoom
        self.height = 1.0*viewport.height/viewport.width * self.width
        self.offset_x = (planet.width - self.width) / 2
        self.offset_y = (planet.height - self.height) / 5
        print self.offset_x, self.offset_y, self.width, self.height, \
                self.viewport.width, self.viewport.height
    
    def convert(self, x, y):
        px = (x - self.offset_x) / self.width * self.viewport.width
        py = self.viewport.height - \
                (y - self.offset_y) / self.height * self.viewport.height
        return (px, py)
        
class Viewport:
    def __init__(self, width, height):
        self.width = width
        self.height = height

class Sprite:
    def __init__(self, source, x_offset, y_offset, width, height, scale):
        self.source = source
        self.source_center = (x_offset + width/2.0, y_offset + height/2.0)
        self.source_dimensions = (width, height)
        self.target_dimensions = (scale*width, scale*height)
    
    def draw(self, canvas, target_center, angle_radians):
        canvas.draw_image(self.source,
                self.source_center, self.source_dimensions,
                target_center, self.target_dimensions,
                angle_radians)
    
class Saucer:
    def __init__(self, frame):
        self.frame = frame
        self.x = self.frame.offset_x + frame.width/2
        self.y = self.frame.offset_y + frame.height/2
        scale = 0.8
        self.saucer = Sprite(sprite_sheet, 0, 0, 68, 45, scale)
        self.static_halo = Sprite(sprite_sheet, 68, 0, 80, 105, scale)
        self.motion_halo = Sprite(sprite_sheet, 148, 0, 80, 105, scale)
        self.velocity_x, self.velocity_y = 0, 0
        self.angle = 0
        self.angle_spring, self.angle_drift = 360, 45  # in degree seconds
    
    def update(self, canvas):
        global keys
        if keys['right'] and not keys['left']:
            self.angle += self.angle_spring
        elif not keys['right'] and keys['left']:
            self.angle -= self.angle_spring
        if not keys['up']:      # when not under boost, let the
            if self.angle > 0:  # angle drift back to zero
                self.angle -= self.angle_drift
            elif self.angle < 0:
                self.angle += self.angle_drift
            halo = self.static_halo
        else:
            radians = math.pi * (self.angle+90*60) / 10800
            self.velocity_x -= BOOST * math.cos(radians)
            self.velocity_y += BOOST * math.sin(radians)
            halo = self.motion_halo
        while self.angle > 180*60:  # force the angle into the range [-pi, pi]
            self.angle -= 360*60
        while self.angle < -180*60:
            self.angle += 360*60
        radians = math.pi * self.angle / 10800   
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.frame.offset_x += self.velocity_x
        self.frame.offset_y += self.velocity_y
        self.velocity_y += GRAVITY
        self.velocity_x *= (1 - FRICTION)
        self.velocity_y *= (1 - FRICTION)
        center = self.frame.convert(self.x, self.y)
        self.saucer.draw(canvas, center, 0)
        halo.draw(canvas, center, radians)
        

def new_game():
    global planet, saucer
    viewport = Viewport(CANVAS_WIDTH, CANVAS_HEIGHT)
    planet = Planet(PLANET_WIDTH, PLANET_HEIGHT)
    frame = Frame(planet, 4, viewport)
    planet.set_frame(frame)
    saucer = Saucer(frame)
    
def draw(canvas):
    if sprite_sheet.get_width() == 0:
        canvas.draw_text('loading images...', (100, 50), 24, '#fff', 'sans-serif')
        return
    planet.update(canvas)
    saucer.update(canvas)

key_codes = {'left': [simplegui.KEY_MAP['left'], simplegui.KEY_MAP['a']],
             'right': [simplegui.KEY_MAP['right'], simplegui.KEY_MAP['d']],
             'up': [simplegui.KEY_MAP['up'], simplegui.KEY_MAP['w']]}
keys = {'left': False, 'right': False, 'up': False}
def key_down(code):
    for key in keys:
        if code in key_codes[key]:
            keys[key] = True
def key_up(code):
    for key in keys:
        if code in key_codes[key]:
            keys[key] = False

new_game()
frame = simplegui.create_frame('flying saucer', CANVAS_WIDTH, CANVAS_HEIGHT)
frame.set_draw_handler(draw)
frame.set_keydown_handler(key_down)
frame.set_keyup_handler(key_up)
frame.start()
