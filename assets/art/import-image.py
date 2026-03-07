import pyxel
  
pyxel.init(128, 128)
pyxel.images[0].load(0, 0, "./spaceship-small.png")

def update():
        pass

def draw():
        pyxel.cls(8)
        pyxel.blt(0, 0, 0, 0, 0, 128, 128)

pyxel.run(update, draw)