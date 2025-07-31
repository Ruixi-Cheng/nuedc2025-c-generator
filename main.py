import svgwrite
import cairosvg
import os
import random
import math

width_mm = 210
height_mm = 297
margin = 20  # 外框边界宽度
safe_margin = 5  # 安全边界距离
default_font_size = 30  # 默认字体大小 (单位 px)

# 字体文件路径
font_path = "times.ttf"

class Square:
    def __init__(self, x, y, size, angle):
        self.x = x
        self.y = y
        self.size = size
        self.angle = angle
        self.center_x = x + size / 2
        self.center_y = y + size / 2
    
    def get_corners(self):
        """获取旋转后正方形的四个角点坐标"""
        half = self.size / 2
        corners = [
            (-half, -half),  # 左上
            (half, -half),   # 右上
            (half, half),    # 右下
            (-half, half)    # 左下
        ]
        
        angle_rad = math.radians(self.angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        rotated_corners = []
        for corner in corners:
            x_rot = corner[0] * cos_a - corner[1] * sin_a
            y_rot = corner[0] * sin_a + corner[1] * cos_a
            rotated_corners.append((self.center_x + x_rot, self.center_y + y_rot))
        
        return rotated_corners
    
    def get_edges(self):
        """获取正方形的四条边"""
        corners = self.get_corners()
        edges = []
        for i in range(4):
            start = corners[i]
            end = corners[(i + 1) % 4]
            edges.append((start, end))
        return edges

def create_image(filename, square_count=10, min_size=60, max_size=120, generate_digits=True):
    # 确保输出目录存在
    os.makedirs("output/svg", exist_ok=True)
    os.makedirs("output/pdf", exist_ok=True)
    
    dwg = create_bg(filename)
    add_random_squares(dwg, square_count, min_size, max_size, generate_digits)
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
    
    circle_min_x = center_x - radius
    circle_max_x = center_x + radius
    circle_min_y = center_y - radius
    circle_max_y = center_y + radius
    
    return (circle_min_x >= min_x and circle_max_x <= max_x and
            circle_min_y >= min_y and circle_max_y <= max_y)

def point_in_square(px, py, square):
    """检查点是否在正方形内（使用射线法）"""
    corners = square.get_corners()
    
    inside = False
    j = len(corners) - 1
    
    for i in range(len(corners)):
        xi, yi = corners[i]
        xj, yj = corners[j]
        
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    
    return inside

def line_intersect(p1, p2, p3, p4):
    """检查两条线段是否相交"""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4
    
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return False
    
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    
    return (0 <= t <= 1) and (0 <= u <= 1)

def edge_intersect_with_squares(edge, squares, exclude_index):
    """检查边是否与其它正方形相交"""
    p1, p2 = edge
    
    for i, square in enumerate(squares):
        if i == exclude_index:
            continue
            
        edges = square.get_edges()
        for other_edge in edges:
            if line_intersect(p1, p2, other_edge[0], other_edge[1]):
                return True
    
    return False

def is_square_detectable(square, all_squares, index):
    """
    检查正方形是否可检测（至少有两条边和一个角不被遮挡）
    """
    edges = square.get_edges()
    corners = square.get_corners()
    
    visible_edges = 0
    visible_corners = 0
    
    for edge in edges:
        if not edge_intersect_with_squares(edge, all_squares, index):
            visible_edges += 1
    
    for corner in corners:
        px, py = corner
        covered = False
        for i, other_square in enumerate(all_squares):
            if i == index:
                continue
            if point_in_square(px, py, other_square):
                covered = True
                break
        if not covered:
            visible_corners += 1
    
    return visible_edges >= 2 and visible_corners >= 1

def does_digit_overlap(new_center, digit_centers, threshold=40):
    """检查新数字位置是否与已有数字重叠"""
    nx, ny = new_center
    for cx, cy in digit_centers:
        dist = math.hypot(nx - cx, ny - cy)
        if dist < threshold:
            return True
    return False

def get_available_digits(used_digits):
    """获取可用的数字，确保6和9不同时出现"""
    all_digits = set(range(10))
    
    # 如果6和9都已经使用了，返回空集合
    if 6 in used_digits and 9 in used_digits:
        return set()
    
    # 如果6已使用，排除9
    if 6 in used_digits:
        available = all_digits - used_digits - {9}
    # 如果9已使用，排除6
    elif 9 in used_digits:
        available = all_digits - used_digits - {6}
    # 如果6和9都未使用，可以任选其一
    else:
        available = all_digits - used_digits
    
    return available

def add_random_squares(dwg, count, min_size, max_size, generate_digits=True):
    inner_x = margin + safe_margin
    inner_y = margin + safe_margin
    inner_width = width_mm - 2 * margin - 2 * safe_margin
    inner_height = height_mm - 2 * margin - 2 * safe_margin

    placed_squares = []
    square_elements = []  # 存储正方形元素
    digit_elements = []   # 存储数字元素
    digit_centers = []
    used_digits = set()   # 记录已使用的数字
    max_attempts = count * 200
    attempts = 0

    while len(placed_squares) < count and attempts < max_attempts:
        attempts += 1

        size = random.randint(max(1, min_size // 5), max(1, max_size // 5)) * 5

        if size > inner_width or size > inner_height:
            continue

        x = random.uniform(inner_x, width_mm - margin - safe_margin - size)
        y = random.uniform(inner_y, height_mm - margin - safe_margin - size)
        rotation_angle = random.uniform(0, 360)

        if not is_square_in_bounds(x, y, size, rotation_angle, safe_margin):
            continue

        new_square = Square(x, y, size, rotation_angle)
        
        temp_squares = placed_squares + [new_square]
        new_index = len(placed_squares)

        if is_square_detectable(new_square, temp_squares, new_index):
            # 如果需要生成数字，检查可用数字
            if generate_digits:
                # 获取可用数字
                available_digits = get_available_digits(used_digits)
                
                # 如果没有可用数字，跳过这个正方形
                if not available_digits:
                    continue
                
                # 随机选择一个可用数字
                digit = random.choice(list(available_digits))
                center_x = x + size / 2
                center_y = y + size / 2

                # 如果数字重叠，则跳过这个正方形（不添加正方形也不添加数字）
                if does_digit_overlap((center_x, center_y), digit_centers):
                    continue  # 跳过这个正方形
                
                # 数字不重叠，记录数字位置和使用情况
                digit_centers.append((center_x, center_y))
                used_digits.add(digit)

                # 创建数字文本元素
                text_element = dwg.text(
                    str(digit),
                    insert=(size/2, size/2),
                    font_family="Times New Roman, Times, serif",
                    font_size=default_font_size,
                    text_anchor="middle",
                    dominant_baseline="middle",
                    fill="white"
                )
                text_transform = f"translate({x} {y}) rotate({rotation_angle} {size/2} {size/2})"
                text_element.attribs['transform'] = text_transform
                digit_elements.append(text_element)

            # 添加正方形（无论是否生成数字）
            placed_squares.append(new_square)
            square_element = dwg.rect(insert=(0, 0), size=(size, size), fill="black", stroke="none")
            transform = f"translate({x} {y}) rotate({rotation_angle} {size/2} {size/2})"
            square_element.attribs['transform'] = transform
            square_elements.append(square_element)

    # 统一添加所有元素：先添加正方形，再添加数字（确保数字在最上层）
    for square_element in square_elements:
        dwg.add(square_element)
    
    for text_element in digit_elements:
        dwg.add(text_element)

def save_svg(dwg, filename):
    svg_filename = os.path.join("output", "svg", filename)
    pdf_filename = os.path.join("output", "pdf", filename.replace('.svg', '.pdf'))
    
    dwg.saveas(svg_filename)
    print(f"SVG文件已保存为: {svg_filename}")

    cairosvg.svg2pdf(url=svg_filename, write_to=pdf_filename)
    print(f"PDF文件已保存为: {pdf_filename}")

# 主程序：生成60个文件
for i in range(1, 61):
    square_count = random.randint(3, 5)
    min_size = 60
    max_size = 120
    generate_digits = True  # 控制是否生成数字
    
    filename = f"{i}.svg"
    print(f"\n生成第 {i} 个文件: {filename} (目标正方形数量: {square_count}, 尺寸范围: {min_size}-{max_size})")
    create_image(filename, square_count=square_count, min_size=min_size, max_size=max_size, generate_digits=generate_digits)