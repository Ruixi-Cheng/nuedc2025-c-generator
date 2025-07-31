import svgwrite
import cairosvg
import os
import random
import math

width_mm = 210
height_mm = 297
margin = 20  # 外框边界宽度
safe_margin = 5  # 安全边界距离

def create_image(filename, square_count=10, min_size=60, max_size=120):
    # 确保输出目录存在
    os.makedirs("output/svg", exist_ok=True)
    os.makedirs("output/pdf", exist_ok=True)
    
    dwg = create_bg(filename)
    add_random_squares(dwg, square_count, min_size, max_size)
    save_svg(dwg, filename)

def create_bg(filename):
    dwg = svgwrite.Drawing(filename, size=(f"{width_mm}mm", f"{height_mm}mm"), 
                          viewBox=(f"0 0 {width_mm} {height_mm}"))
    
    dwg.add(dwg.rect(insert=(0, 0), size=(width_mm, height_mm), 
                     fill="black", stroke="none"))
    
    inner_x = margin
    inner_y = margin
    inner_width = width_mm - 2 * margin
    inner_height = height_mm - 2 * margin
    
    dwg.add(dwg.rect(insert=(inner_x, inner_y), 
                     size=(inner_width, inner_height), 
                     fill="white", stroke="none"))
    
    return dwg

def is_square_in_bounds(x, y, size, angle, safe_margin):
    center_x = x + size / 2
    center_y = y + size / 2
    
    diagonal = size * math.sqrt(2)
    radius = diagonal / 2
    
    min_x = margin + safe_margin
    max_x = width_mm - margin - safe_margin
    min_y = margin + safe_margin
    max_y = height_mm - margin - safe_margin
    
    # 检查圆形包围盒是否在边界内
    circle_min_x = center_x - radius
    circle_max_x = center_x + radius
    circle_min_y = center_y - radius
    circle_max_y = center_y + radius
    
    return (circle_min_x >= min_x and circle_max_x <= max_x and
            circle_min_y >= min_y and circle_max_y <= max_y)

def add_random_squares(dwg, count, min_size, max_size):
    # 计算可用区域（内框区域，考虑安全距离）
    inner_x = margin + safe_margin
    inner_y = margin + safe_margin
    inner_width = width_mm - 2 * margin - 2 * safe_margin
    inner_height = height_mm - 2 * margin - 2 * safe_margin
    
    placed_squares = 0
    max_attempts = count * 50
    attempts = 0
    
    while placed_squares < count and attempts < max_attempts:
        attempts += 1
        
        # 控制最大尺寸不超过可用区域
        max_allowed_size = min(inner_width, inner_height)
        actual_max_size = min(max_size, max_allowed_size)
        actual_min_size = min(min_size, actual_max_size)
        
        if actual_min_size > actual_max_size or actual_max_size <= 0:
            continue  # 区域太小，无法放置任何正方形

        # 生成符合要求的尺寸（5的倍数）
        size = random.randint(max(1, actual_min_size // 5), max(1, actual_max_size // 5)) * 5

        if size > inner_width or size > inner_height:
            continue

        max_x = width_mm - margin - safe_margin - size
        max_y = height_mm - margin - safe_margin - size
        min_x = margin + safe_margin
        min_y = margin + safe_margin
        
        if max_x < min_x or max_y < min_y:
            continue

        x = random.uniform(min_x, max_x)
        y = random.uniform(min_y, max_y)

        rotation_angle = random.uniform(0, 360)
        
        if not is_square_in_bounds(x, y, size, rotation_angle, safe_margin):
            continue  # 超出边界，跳过

        square = dwg.rect(insert=(0, 0), size=(size, size), fill="black", stroke="none")
        transform = f"translate({x} {y}) rotate({rotation_angle} {size/2} {size/2})"
        square.attribs['transform'] = transform

        dwg.add(square)
        placed_squares += 1

def save_svg(dwg, filename):
    # 生成完整的文件路径
    svg_filename = os.path.join("output", "svg", filename)
    pdf_filename = os.path.join("output", "pdf", filename.replace('.svg', '.pdf'))
    
    dwg.saveas(svg_filename)
    print(f"SVG文件已保存为: {svg_filename}")

    cairosvg.svg2pdf(url=svg_filename, write_to=pdf_filename)
    print(f"PDF文件已保存为: {pdf_filename}")


for i in range(1, 11):
    square_count = random.randint(2, 4)
    min_size = 60
    max_size = 120
    
    filename = f"{i}.svg"
    print(f"\n生成第 {i} 个文件: {filename} (正方形数量: {square_count}, 尺寸范围: {min_size}-{max_size})")
    create_image(filename, square_count=square_count, min_size=min_size, max_size=max_size)