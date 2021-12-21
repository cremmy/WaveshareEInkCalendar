import math


def draw_line_dashed(draw, xy, fill=None, width=0, dash=4, space=4, phase=0):
    if len(xy) < 1:
        raise TypeError
    if type(xy[0]) is not tuple:
        newxy = []
        for i in range(0, len(xy), 2):
            newxy.append((xy[i + 0], xy[i + 1]))
        xy = newxy

    is_dash = True

    phase = phase - int(phase)
    leftover = int(phase * (dash + space))
    if leftover == 0:
        pass
    elif leftover <= space:
        is_dash = False
    elif leftover > space:
        leftover = leftover - space

    for i in range(0, len(xy) - 1):
        xy0 = xy[i + 0]
        xy1 = xy[i + 1]

        veclen = math.sqrt((xy1[0] - xy0[0]) ** 2 + (xy1[1] - xy0[1]) ** 2)
        direction = ((xy1[0] - xy0[0]) / veclen, (xy1[1] - xy0[1]) / veclen)

        drawnlen = 0
        while drawnlen < veclen:
            drawlen = dash if is_dash else space
            if leftover > 0:
                drawlen = min(leftover, drawlen)
                leftover = leftover - drawlen
            if drawlen + drawnlen > veclen:
                leftover = drawlen + drawnlen - veclen
                drawlen = veclen - drawnlen

            fxy0 = (xy0[0] + direction[0] * drawnlen, xy0[1] + direction[1] * drawnlen)
            fxy1 = (
                xy0[0] + direction[0] * (drawnlen + drawlen - 1), xy0[1] + direction[1] * (drawnlen + drawlen - 1))

            if is_dash:
                draw.line([fxy0, fxy1], fill, width)
            drawnlen = drawnlen + drawlen
            if leftover == 0:
                is_dash = not is_dash


def draw_rectangle_dashed(draw, xy, outline=None, width=0, dash=4, space=4, phase=0):
    if len(xy) != 2 and len(xy) != 4:
        raise TypeError

    if type(xy[0]) is not tuple:
        xy = [(xy[0], xy[1]), (xy[2], xy[3])]

    draw_line_dashed(draw, [
        (xy[0][0], xy[0][1]),
        (xy[1][0], xy[0][1]),
        (xy[1][0], xy[1][1]),
        (xy[0][0], xy[1][1]),
        (xy[0][0], xy[0][1]),
    ], outline, width, dash, space, phase)
