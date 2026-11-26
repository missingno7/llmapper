import sys
import rite as rite_mod
from rite import *
from PIL import ImageDraw, ImageFont, ImageFilter
from city3d import BASE, WATER, Y1
rite_mod.FL = BASE - .03


VERSION = 'V0.1'


def title_tex(C, txt='GRAVESEND', font='BERNHC.TTF', space=34, key=-1):
    f = ImageFont.truetype('C:/Windows/Fonts/' + font, 300)
    L = Image.new('L', (4000, 500), 0)
    d = ImageDraw.Draw(L)
    x = 60
    for a, b in zip(txt, txt[1:] + ' '):
        d.text((x, 20), a, font=f, fill=255)
        x += f.getlength(a + b) - f.getlength(b) + space
    L = L.crop(L.getbbox())
    pad = 20
    M = Image.new('L', (L.width + 2 * pad, L.height + 2 * pad), 0)
    M.paste(L, (pad, pad))
    g = np.random.default_rng(4)
    n = sum(np.asarray(Image.fromarray((g.random((M.height // s + 2, M.width // s + 2)) * 255).astype('u1')).resize(M.size, 3)).astype(float) / 255 * w
            for s, w in ((4, .3), (11, .4), (40, .3)))
    e = np.asarray(M.filter(ImageFilter.GaussianBlur(4))).astype(float) / 255
    a = ((e > (.34 + .5 * (n - .42))) * 255).astype('u1')
    k = np.linspace(0, 1, M.height)[:, None] + .35 * (n - .5)
    col = np.stack([np.interp(k, [0, .5, 1], c) for c in ([236, 226, 206], [222, 206, 178], [168, 120, 92])], -1) * (.65 + .6 * n)[..., None]
    tx = C.ctx.texture(M.size, 4, np.dstack([np.clip(col, 0, 255).astype('u1'), a]).tobytes())
    tx.build_mipmaps()
    tx.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
    tx.anisotropy = 16
    C.tex[(key, 0)] = tx
    return M.width / M.height


def plate(asp, h=4.9, cx=29., drop=0.):
    cy, z, w = (WATER + BASE) / 2 - drop, Y1 + .06, h * asp
    q = [((cx - w / 2, cy + h / 2), (0, 0)), ((cx + w / 2, cy + h / 2), (1, 0)), ((cx + w / 2, cy - h / 2), (1, 1)), ((cx - w / 2, cy - h / 2), (0, 1))]
    return [(q[j][0][0], q[j][0][1], z, *q[j][1], 0, 0, 1, 1.) for j in (0, 1, 2, 0, 2, 3)]


def scene(C, R=49.5, disc=5.0, blood=.16, emt=.16, rot=0, **kw):
    rite_mod.BLOOD = blood
    dec, discs, cand, six = rite(R=R, disc=disc, blood=blood, rot=rot)
    asp = title_tex(C)
    dec.append((plate(asp), -1, (.72, .92, 1.25), emt, 1.0))
    v = title_tex(C, VERSION, space=10, key=-2)
    vh = 2.8
    dec.append((plate(v, vh, 29 + 4.9 * asp / 2 + 1.3 + vh * v / 2, (4.9 - vh) / 2 - .12), -2, (.72, .92, 1.25), emt, 1.0))
    li = [(p[0], BASE + 4, p[1], 16., 1.0, .22, .10, 0) for p in six]
    li += [(x, -6.2, Y1 + 5, 17., 1.7, 1.0, .62, 0) for x in (5, 17, 29, 41, 53)]
    li += [(x, -3., -50, 48., 5., .5, .2, 0) for x in (-8, 29, 66)]
    li += [(27.4, 6.4, 44.6, 4.6, 12., 8.4, 5., 0)]                     # the obelisk, or it is lost against the church wall
    return dict(amb=(.95, .78, .80), sun=(2.0, .95, .68), decals=dec, discs=discs, candles=cand, lights=li, plane=(1.9, 0, 0),
                lampk=10., roomgain=2.2, exposure=1.45, floork=.10, sidek=.35)
