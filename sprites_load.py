import pyxel

pyxel.init(256, 256)
pyxel.load("pocket_world.pyxres", exclude_sounds=True, exclude_musics=True, exclude_tilemaps=True)

# Export
# pyxel.images[0].save("sprites.png", scale=1)

# Import (nach dem Bearbeiten in Procreate)
pyxel.images[1].load(0, 0, "sprites_png/sprites.png")
pyxel.save("pocket_world.pyxres")