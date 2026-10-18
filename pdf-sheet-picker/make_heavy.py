"""Heavy CAD-like set: 40 sheets, each with ~20k vector line segments and ~2k small text labels."""
import random, pymupdf
random.seed(7)
doc = pymupdf.open()
for k in range(40):
    p = doc.new_page(width=2592, height=1728)
    sh = p.new_shape()
    for _ in range(20000):
        x, y = random.uniform(50, 2000), random.uniform(50, 1250)
        sh.draw_line((x, y), (x + random.uniform(-30, 30), y + random.uniform(-30, 30)))
    sh.finish(width=0.3); sh.commit()
    for _ in range(2000):
        p.insert_text((random.uniform(50, 2000), random.uniform(60, 1250)), f"C{random.randint(1,999)}", fontsize=5)
    p.insert_text((2300, 1650), f"{'E' if k % 3 == 0 else 'A'}{k // 10}.{k % 10:02d}", fontsize=48)
doc.save("fixtures/heavy40.pdf", deflate=True)
