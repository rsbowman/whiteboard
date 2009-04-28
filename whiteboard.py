#!/usr/bin/python

import sys, os
from tempfile import TemporaryFile

from PIL import Image

x11_colors = {
    'r': 'rgb:f/0/0',
    'g': 'rgb:0/f/0',
    'b': 'rgb:0/0/f',
    'k': 'rgb:0/0/0'
    }

svg_colors = {
    'r': 'ff0000',
    'g': '00ff00',
    'b': '0000ff',
    'k': '000000'
    }

hex_colors = {
    (0, 0, 0) : 'k',
    (0xff, 0, 0): 'r',
    (0, 0xff, 0): 'g',
    (0, 0, 0xff): 'b'
    }

    

def simple_diagram_to_svg(infile, outfile, threshold, output_width):
    infile_base, extension = os.path.splitext(infile)
    
    thresholded_file = '%s_threshold%s' %(infile_base, extension)
    print 'reducing'
    reduce_colors(infile, thresholded_file, threshold)

    print 'neighborizing'
    neighbor_file = '%s_neighbor%s' %(infile_base, extension)
    new_image, unique_colors = neighborhood_threshold(
        Image.open(thresholded_file))
    new_image.save(neighbor_file)

    ppm_file = '%s_ppm.ppm' %(infile_base,)

    os.system('convert %s %s' %(neighbor_file, ppm_file))

    print 'potracing'
    for color in unique_colors:
        traced_outfile = '%s_%s.svg' %(infile_base, hex_colors[color])
        ppm_color = 'rgb:%.2x/%.2x/%.2x' %color
        potrace_color = "'#%.2x%.2x%.2x'" %color
        potrace_cmd = "cat %s | ppmcolormask %s | potrace --svg --color %s > %s"
        cmd = potrace_cmd %(ppm_file, ppm_color,
                            potrace_color, traced_outfile)
        #print cmd
        os.system(cmd)

    svg_files = ['%s_%s.svg'%(infile_base, hex_colors[color])
                 for color in unique_colors]
    concat_svg_files(svg_files, '%s.svg' %(infile_base,))

    cmd = 'inkscape -f %s.svg -e %s -w %d' %(infile_base, outfile,
                                             output_width)
    print cmd
    os.system(cmd)
    
    if True:
        os.remove(thresholded_file)
        os.remove(neighbor_file)
        os.remove(ppm_file)
        for svg_file in svg_files:
            os.remove(svg_file)

    print 'yay!'
                         
def reduce_colors(infile, outfile, threshold):
    os.system('convert %s -separate -threshold %d%% -combine %s' %
              (infile, threshold, outfile))
##    colors = [(-1, -1, -1), (0xff, 0, 0), (0, 0xff, 0),
## (0, 0, 0xff), (0xff, 0xff, 0xff)]
##    im = Image.open(infile)
##   thresh = image_threshold(im, colors)
##    thresh.save(outfile)
    
def mkbitmap(infilename, outfilename, opts=''):
    assert infilename[-4] == '.' and len(fname[-4:]) == 4
    ppmfname = infilename[:-4] + '.ppm'
    outppm = infilename[:-4] + "_out.ppm"
    os.system('convert %s %s' %(infilename, ppmfname))
    os.system('mkbitmap %s %s -o %s' %(opts, ppmfname, outppm))
    os.system('convert %s %s' %(outppm, outfilename))

    os.system('rm %s %s' %(ppmfname, outppm))
    
    return 0


def dist_sq(x, y):
    #return sum((abs(x_i - y_i) for x_i, y_i in zip(x, y)))
    return sum(((x_i - y_i)**2 for x_i, y_i in zip(x, y)))

def closest(pt, pts):
    distance_pts = [(dist_sq(pt, pt_i), pt_i) for pt_i in pts]
    return min(distance_pts)[1]

def image_threshold(image, colors):
    """ for each pixel of an image, color the output image the
    euclidean closest element of colors argument"""
    out_image = image.copy()
    out_array = out_image.load()

    width, height = image.size
    for col in range(width):
        for row in range(height):
            out_array[col, row] = closest(out_array[col, row], colors)

    return out_image

red = (0xff, 0, 0)
green = (0, 0xff, 0)
blue = (0, 0, 0xff)
black = (0, 0, 0)

def neighborhood_threshold(input_image, bg=(0xff, 0xff, 0xff),
                           allowed_colors=[red, green, blue, black]):
    image = input_image.copy()
    im_array = image.load()
    unique_colors = []
    
    radius = 3
    width, height = image.size

    for col in range(width):
        for row in range(height):
            if im_array[col, row] != bg:
                is_ambiguous = True
                current_radius = radius - 1
                
                while is_ambiguous:
                    current_radius += 1
                    pixels_of_color = neighborhood_colors(im_array, col,
                                                          row, width, height,
                                                          current_radius)
                    reduced_colors = [(pixels_of_color.get(color, 0), color)
                                      for color in allowed_colors]
                    n_pixels, new_color = max(reduced_colors)
                    is_ambiguous = n_pixels <= 0

                im_array[col, row] = new_color
                if new_color not in unique_colors:
                    unique_colors.append(new_color)

                    
                ## if colors.has_key(bg): del colors[bg]
                ## # return color whose value is largest
                ## new_color = max([(value, key) for key, value in colors.items()])[1]
                ## im_array[col, row] = new_color
                ## if new_color not in unique_colors:
                ##     unique_colors.append(new_color)

    return image, unique_colors

def neighborhood_colors(im_array, col, row, width, height, radius):
    colors = {}
    
    for col_ofs in range(-radius, radius + 1):
        for row_ofs in range(-radius, radius + 1):
            if ((col_ofs)**2 + (row_ofs)**2 <= radius**2 and
                0 <= col + col_ofs < width and
                0 <= row + row_ofs < height):
                pixel = im_array[col + col_ofs, row + row_ofs]
                colors[pixel] = colors.get(pixel, 0) + 1

    return colors

from xml.etree import ElementTree as ET

def concat_svg_files(files, outfile):
    groups = []
    svg_output = ET.parse(files[0])
    svg_root = svg_output.getroot()
    files = files[1:]
    
    for f in files:
        svg = ET.parse(f)
        groups.extend(svg.findall('{http://www.w3.org/2000/svg}g'))

    for g in groups:
        svg_root.insert(1, g)

    ET.ElementTree(svg_root).write(outfile)

    
from optparse import OptionParser

def main(argv):
    usage = "usage: %prog [options] input_file"
    parser = OptionParser(usage=usage)

    parser = OptionParser()
    parser.set_defaults(threshold=30)
    parser.add_option('-t', '--threshold',
                      help="threshold value for quantitization",
                      dest="threshold")

    parser.set_defaults(output_width=200)
    parser.add_option('-w', '--width',
                      help="width of output image",
                      type="int", dest="output_width")
    
    options, args = parser.parse_args()
    if len(args) < 1:
        parser.error("need an input")

    for infile in args:
        infilebase, ext = os.path.splitext(infile)
        outfile = infilebase + '_whiteboard' + ext
        print '%s -> %s' %(infile, outfile)
        simple_diagram_to_svg(infile, outfile,
                              threshold=options.threshold,
                              output_width=options.output_width)
    
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))    
