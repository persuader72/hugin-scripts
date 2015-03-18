import hsi
import subprocess
import copy
import os
import sys

# This script pre-align photos and search controlpoints on a set of ordered photo
# taken for example from a UAV.

#  UAV Fotografic Path          X(row,col) = Photomosaic reference
#       ___     ___             Tot(row,col) = Total number of rows and cols
#  *   *   *  5*   *4 rwN       Olap(%rows,%cols) longitudinal and trasversal photo overlap size
#  |   |   |   |   |
#  *   *   *  6*   *3 rw3       UAV aerial path is supposed to be contained in a square area each shot
#  |   |   |   |   |            must be taken to obtain the desiderd overlap between photos
#  *   *   X  7*   *2 rw2
#  |   |   |   |   |
#  *   *   *   *   *1 rw1
#  |   |   |   |   |
#  *___*   *___*   *0 (Start)
#
# Ncl cl3 cl2 cl1 cl0

#totcols = 5
#totrows = 39

#overlaprow = 0.30
#overlapcol = 0.50

#center_row = 18
#center_col = 2
#centernum = 97

#startfrom = 83

totcols = 6
totrows = 27

overlapcol = 0.50
overlaprow = 0.11

center_col = 3
center_row = 16

centernum = 109

startfrom = 0

def are_valid_coordinates(row, col):
    global totrows
    global totcols

    return row >=0 and row < totrows and col >=0 and col < totcols


def from_inndex_to_coords(index):
    global totrows
    global totcols

    row = index % totrows
    col = index / totrows
    odd = True if col % 2 == 1 else False
    row = totrows - row - 1 if odd else row
    return (row, col)


def from_coords_to_index(row, col):
    global totrows
    global totcols

    odd = True if col % 2 == 1 else False
    row = totrows - row - 1 if odd else row
    return totrows * col + row


def relative_coords(row, col):
    global center_row
    global center_col

    drow = -(row - center_row)
    dcol = -(col - center_col)
    return (drow, dcol)


def run_helper_program(args, mute=True):
    try:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as problem:
        message = ('OS error: "%s"\nwhen trying to execute:\n  %s\n' % (problem.strerror, args))
        raise Exception(message)

    p.wait()
    output = p.stdout.readlines()

    if not mute:
        for l in output:
            print l.strip()

    # vpr ( '%s returned %d' % ( args[0] , p.returncode ) )
    return p.returncode, output


def read_metadata(filename):
    meta = []
    imagenum = 0
    with open(filename, 'r') as filein:
        for line in filein:
            fields = line.strip().split(';')
            if len(fields) > 1:
                fields.append(imagenum)
                meta.append(fields)
                if len(fields[4]) > 1:
                    imagenum += 1
    return meta


def metadata_index_of(metadata, index, imagename):
    if metadata is None:
        return index
    else:
        index = 0
        for m in metadata:
            if imagename[0:8] == m[4][0:8]:
                return index
            index += 1
        return index


def metadata_reverse_index_of(metadata, index):
    if metadata is None:
        return index
    else:
        if index >= len(metadata) or len(metadata[index][4]) == 0:
            return -1
        else:
            return metadata[index][5]


def prealign(inpto, outpto):
    counter = 0

    with open(outpto, 'w') as fileout:
        with open(inpto,'r') as filein:
            for line in filein:
                if len(line)>0 and line[0] == 'i':

                    (row, col) = from_inndex_to_coords(counter)
                    (drow, dcol) = relative_coords(row, col)

                    myx = dcol * overlapcol
                    myy = drow * overlaprow

                    print " %d %d , %f %f" % (drow, dcol, myx, myy)

                    newfileds = []
                    fields = line.split(' ')
                    for field in fields:
                        prefix = field[0:3]
                        if prefix == "TrX":
                            field = "TrX%f" % myx
                        elif prefix == "TrY":
                            field = "TrY%f" % myy
                        newfileds.append(field)
                    line = ' '.join(newfileds)
                    counter += 1

                fileout.write(line)


def prealign2(inpto, outpto, metafile):
    metadata = None
    p = hsi.Panorama()
    ifs = hsi.ifstream(inpto)
    p.readData(ifs)
    del ifs

    for idx1 in range(startfrom, nimgs):
        image = p.getImage(idx1)
        """ :type : hsi.SrcPanoImage"""
        (row, col) = from_inndex_to_coords(idx1)
        (drow, dcol) = relative_coords(row, col)

        myx = dcol * overlapcol
        myy = drow * overlaprow

        print "%d %dx%d %fx%f" % (idx1, row,col,myx,myy)

        image.setX(myx)
        image.setY(myy)

    ofs = hsi.ofstream(outpto)
    p.writeData(ofs)
    del ofs


def optimize(inpto, outpto):
    p = hsi.Panorama()
    ifs = hsi.ifstream(inpto)
    p.readData(ifs)
    del ifs

    vars = ()
    nimgs = p.getNrOfImages()
    for i in range(0, nimgs):
        vars += (('TrX', 'TrY'),)
    print vars

    p.setOptimizeVector(vars)

    ofs = hsi.ofstream(outpto)
    p.writeData(ofs)
    del ofs

def main(inpto, outpto, metafile):
    p = hsi.Panorama()
    ifs = hsi.ifstream(inpto)
    p.readData(ifs)
    del ifs

    if startfrom == 0:
        p.setCtrlPoints(hsi.CPVector())
    nimgs = p.getNrOfImages()

    idx1 = 0
    for idx1 in range(startfrom, nimgs):
        if os.path.exists('stop'):
            break

        i1 = p.getImage(idx1)
        """ :type : hsi.SrcPanoImage"""
        (row1, col1) = from_inndex_to_coords(idx1)
        neighboors = [(1, 0), (2, 0), (0, 1), (1, 1)]

        for neighboor in neighboors:
            row2 = row1+neighboor[0]
            col2 = col1+neighboor[1]

            if are_valid_coordinates(row2, col2):
                idx2 = from_coords_to_index(row2, col2)
                if idx2 < 0:
                    continue

                i2 = p.getImage(idx2)
                """ :type : hsi.SrcPanoImage"""
                # print (row1, col1, row2, col2, idx2)


                tmp_filename = '__%s' % inpto
                cpfind_input = '_%s' % inpto

                ofs = hsi.ofstream(cpfind_input)
                warp = hsi.Panorama()
                wi0 = copy.copy(i1)
                wi1 = copy.copy(i2)
                warp.addImage(wi0)
                warp.addImage(wi1)
                warp.writeData(ofs)
                del ofs

                #command = ['cpfind', '--fullscale','--multirow' , '--sieve2size', '5', '--ransacmode', 'hom', '-o', tmp_filename, cpfind_input]
                command = ['autopano-sift-c',  '--projection' , '%d,30' % hsi.PanoramaOptions.RECTILINEAR , '--maxmatches' , '25' , tmp_filename]
                command += [i1.getFilename(), i2.getFilename()]
                mute_command_output = True

                print "%d <-> %d , %s <-> %s" % (idx1, idx2, i1.getFilename(), i2.getFilename())
                print ' '.join(command)
                run_helper_program(command, mute_command_output)

                ifs = hsi.ifstream(tmp_filename)
                warp = hsi.Panorama()
                warp.readData(ifs)
                del ifs

                cpv = warp.getCtrlPoints()
                """ :type : list[hsi.ControlPoint]"""

                print "Found %d ctrlpts" % len(cpv)

                os.remove(tmp_filename)
                os.remove(cpfind_input)

                for cp in cpv:
                    p.addCtrlPoint(hsi.ControlPoint(idx1, cp.x1, cp.y1, idx2, cp.x2, cp.y2, hsi.ControlPoint.X_Y))

    print "Loop exted at iteration %d" % idx1

    ofs = hsi.ofstream(outpto)
    p.writeData(ofs)
    del ofs


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='args')
    parser.add_argument('-a', '--action', metavar='<action type>', type=str)
    parser.add_argument('-o', '--output', metavar='<pto output>', type=str, default=None)
    parser.add_argument('-m', '--metadata', metavar='<metafata>', type=str, default=None)
    parser.add_argument('input', metavar='<pto input>', type=str, default=None)

    if len(sys.argv) < 2:
        parser.print_help()
        exit()

    args = parser.parse_args()

    if args.action is None or args.input is None or args.output is None:
        parser.print_help()
        exit()

    if args.action == 'searchcp':
        main(args.input, args.output, args.metadata)
    elif args.action == 'prealign':
        prealign2(args.input, args.output, args.metadata)
    elif args.action == 'optimize':
        optimize(args.input, args.output)