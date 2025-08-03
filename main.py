import svgwrite
import cairosvg
import os
import random
import math
from PIL import Image
import io
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, MofNCompleteColumn

# --- 配置 ---
width_mm = 210
height_mm = 297
margin = 20
safe_margin = 5
default_font_size = 30

# --- 新增：控制标志 ---
ENABLE_BOLD = True        # 是否启用加粗字体生成
ENABLE_OTHER_FONTS = True # 是否启用除 Times New Roman 之外的其他字体生成

# --- 修改：定义字体配置 ---
# 字体配置字典: {显示名称: (用于文件夹命名, 普通字体族, 加粗字体族)}
# 注意：CSS 中的加粗通常通过 font_weight="bold" 实现，所以普通和加粗的字体族字符串可以相同。
#       这里分开定义是为了未来可能的扩展（例如使用不同的 .ttf 文件）。
FONT_CONFIGS = {
    "Times New Roman": ("Times_New_Roman", "Times New Roman, Times, serif", "Times New Roman, Times, serif"),
    "Arial": ("Arial", "Arial, Helvetica, sans-serif", "Arial, Helvetica, sans-serif"),
    "Noto Sans": ("Noto_Sans", "Noto Sans, Arial, sans-serif", "Noto Sans, Arial, sans-serif"),
    "Noto Serif": ("Noto_Serif", "Noto Serif, Times New Roman, serif", "Noto Serif, Times New Roman, serif"),
}

# --- 修改：定义字体选择权重 ---
# Times New Roman 占 60%，其他字体平分 40%
FONT_WEIGHTS = {"Times New Roman": 60}
if ENABLE_OTHER_FONTS:
    other_fonts = [name for name in FONT_CONFIGS.keys() if name != "Times New Roman"]
    if other_fonts:
        remaining_weight = 100 - FONT_WEIGHTS["Times New Roman"]
        weight_per_other_font = remaining_weight / len(other_fonts)
        for font_name in other_fonts:
            FONT_WEIGHTS[font_name] = weight_per_other_font
else:
    # 如果不启用其他字体，则 Times New Roman 占 100%
    FONT_WEIGHTS["Times New Roman"] = 100

# --- 修改：定义加粗字体生成概率 ---
# 这是针对 *每个* 选定字体，决定是否使用加粗样式的概率
BOLD_PROBABILITY = 0.3 # 30%

# --- 新增：辅助函数：根据权重随机选择字体 ---
def choose_font_by_weight(font_weights):
    """根据给定的权重字典随机选择一个字体名称"""
    fonts = list(font_weights.keys())
    weights = list(font_weights.values())
    # random.choices 返回一个列表，[0] 获取第一个（也是唯一一个）元素
    chosen_font_name = random.choices(fonts, weights=weights, k=1)[0]
    return chosen_font_name

class Square:
    def __init__(self, x, y, size, angle):
        self.x = x
        self.y = y
        self.size = size
        self.angle = angle
        self.center_x = x + size / 2
        self.center_y = y + size / 2

    def get_corners(self):
        half = self.size / 2
        corners = [(-half, -half), (half, -half), (half, half), (-half, half)]
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
        corners = self.get_corners()
        edges = []
        for i in range(4):
            start = corners[i]
            end = corners[(i + 1) % 4]
            edges.append((start, end))
        return edges

def create_image(filename, square_count=10, min_size=60, max_size=120, generate_digits=True):
    os.makedirs("output/svg", exist_ok=True)
    os.makedirs("output/pdf", exist_ok=True)
    dwg = create_bg(filename)
    # --- 修改：传递字体信息和控制标志 ---
    add_random_squares(
        dwg, square_count, min_size, max_size, generate_digits,
        FONT_CONFIGS, FONT_WEIGHTS, BOLD_PROBABILITY,
        ENABLE_BOLD, ENABLE_OTHER_FONTS
    )
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
    nx, ny = new_center
    for cx, cy in digit_centers:
        dist = math.hypot(nx - cx, ny - cy)
        if dist < threshold:
            return True
    return False

def get_available_digits(used_digits):
    all_digits = set(range(10))
    if 6 in used_digits and 9 in used_digits:
        return set()
    if 6 in used_digits:
        available = all_digits - used_digits - {9}
    elif 9 in used_digits:
        available = all_digits - used_digits - {6}
    else:
        available = all_digits - used_digits
    return available

# --- 修改：函数签名增加字体配置和控制标志 ---
def add_random_squares(
    dwg, count, min_size, max_size, generate_digits,
    font_configs, font_weights, bold_probability,
    enable_bold, enable_other_fonts
):
    inner_x = margin + safe_margin
    inner_y = margin + safe_margin
    inner_width = width_mm - 2 * margin - 2 * safe_margin
    inner_height = height_mm - 2 * margin - 2 * safe_margin
    placed_squares = []
    square_elements = []
    digit_elements = []
    digit_centers = []
    used_digits = set()
    max_attempts = count * 200
    attempts = 0
    # --- 修改：存储用于裁剪的数字信息，包括字体信息 ---
    digits_for_crop = []
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
            if generate_digits:
                available_digits = get_available_digits(used_digits)
                if not available_digits:
                    continue
                digit = random.choice(list(available_digits))
                center_x = x + size / 2
                center_y = y + size / 2
                if does_digit_overlap((center_x, center_y), digit_centers):
                    continue

                # --- 新增：根据权重选择字体 ---
                selected_font_name = choose_font_by_weight(font_weights)
                font_display_name, font_regular, font_bold = font_configs[selected_font_name]

                # --- 新增：决定是否使用加粗样式 (受 ENABLE_BOLD 和 BOLD_PROBABILITY 控制) ---
                use_bold = False
                if enable_bold and random.random() < bold_probability:
                    use_bold = True

                current_font = font_bold if use_bold else font_regular
                # --- 新增：记录字体信息，用于文件夹命名 ---
                # 文件夹名：Times_New_Roman 或 Times_New_Roman_Bold 等
                font_folder_suffix = "_Bold" if use_bold else ""
                font_folder_name = f"{font_display_name}{font_folder_suffix}"

                digit_centers.append((center_x, center_y))
                used_digits.add(digit)
                # --- 修改：记录数字信息以便裁剪，包含字体信息 ---
                digits_for_crop.append({
                    'digit': digit,
                    'center': (center_x, center_y),
                    'rotation': rotation_angle,
                    'size': size,
                    'font': current_font, # 用于SVG文本元素
                    'font_folder_name': font_folder_name, # 用于文件夹命名
                    'selected_font_name': selected_font_name # 用于调试/日志 (可选)
                })

                # --- 修改：使用 current_font 和 font_weight ---
                text_element = dwg.text(
                    str(digit),
                    insert=(size/2, size/2),
                    font_family=current_font, # 使用选定的字体族
                    font_size=default_font_size,
                    font_weight="bold" if use_bold else "normal", # CSS 设置加粗
                    text_anchor="middle",
                    dominant_baseline="middle",
                    fill="white"
                )
                text_transform = f"translate({x} {y}) rotate({rotation_angle} {size/2} {size/2})"
                text_element.attribs['transform'] = text_transform
                digit_elements.append(text_element)
            placed_squares.append(new_square)
            square_element = dwg.rect(insert=(0, 0), size=(size, size), fill="black", stroke="none")
            transform = f"translate({x} {y}) rotate({rotation_angle} {size/2} {size/2})"
            square_element.attribs['transform'] = transform
            square_elements.append(square_element)

    for square_element in square_elements:
        dwg.add(square_element)
    for text_element in digit_elements:
        dwg.add(text_element)

    # --- 修改：传递字体信息给导出函数 ---
    # 为了简化，我们传递 FONT_CONFIGS 的第一个 key (Times New Roman) 的 display_name 作为基础名称
    # 或者传递一个通用的噪声基础名称
    base_noise_font_name = FONT_CONFIGS["Times New Roman"][0] # "Times_New_Roman"
    export_digits_as_png(dwg, digits_for_crop)
    export_noise_images(dwg, placed_squares, digits_for_crop, noise_count=4, base_noise_font_name=base_noise_font_name)

# --- 修改：导出函数签名和实现 ---
def export_digits_as_png(dwg, digits_for_crop):
    full_svg_data = dwg.tostring()
    for info in digits_for_crop:
        digit = info['digit']
        center_x, center_y = info['center']
        rotation = info['rotation']
        size = info['size']
        font_for_element = info['font']
        font_folder_name = info['font_folder_name'] # 例如 "Times_New_Roman" 或 "Arial_Bold"
        # selected_font_name = info['selected_font_name'] # 可选

        # --- 修改：根据字体信息确定输出路径 ---
        # output/[字体文件夹名]/[数字]
        output_dir = os.path.join("output", font_folder_name, str(digit))
        os.makedirs(output_dir, exist_ok=True)
        png_path = os.path.join(output_dir, f"{int(center_x)}_{int(center_y)}.png")

        crop_size = size / 2
        half_crop = crop_size / 2
        viewbox_x = center_x - half_crop
        viewbox_y = center_y - half_crop
        viewbox_width = crop_size
        viewbox_height = crop_size

        # --- 修改：创建局部SVG ---
        local_svg_data = full_svg_data.replace(
            f'viewBox="0 0 {width_mm} {height_mm}"',
            f'viewBox="{viewbox_x} {viewbox_y} {viewbox_width} {viewbox_height}"'
        )

        try:
            png_data = cairosvg.svg2png(
                bytestring=local_svg_data.encode('utf-8'),
                output_width=60,
                output_height=60
            )
            img = Image.open(io.BytesIO(png_data))
            img.save(png_path)
            print(f"✅ 已保存数字 {digit} (字体: {font_folder_name}) 的图像到: {png_path}")
        except Exception as e:
            print(f"❌ 导出数字 {digit} (字体: {font_folder_name}) 图像失败: {e}")
            print(f"ViewBox: {viewbox_x}, {viewbox_y}, {viewbox_width}, {viewbox_height}")
            print(f"Crop size: {crop_size}")

def calculate_rectangle_overlap_area(rect1, rect2):
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2
    overlap_x1 = max(x1, x2)
    overlap_y1 = max(y1, y2)
    overlap_x2 = min(x1 + w1, x2 + w2)
    overlap_y2 = min(y1 + h1, y2 + h2)
    if overlap_x1 >= overlap_x2 or overlap_y1 >= overlap_y2:
        return 0.0
    overlap_width = overlap_x2 - overlap_x1
    overlap_height = overlap_y2 - overlap_y1
    return overlap_width * overlap_height

# --- 修改：导出噪声函数签名和实现 ---
def export_noise_images(dwg, placed_squares, digits_info, noise_count=1, overlap_threshold=0.4, base_noise_font_name="Times_New_Roman"):
    """噪声图像不区分字体，统一存放在 output/noise 下"""
    full_svg_data = dwg.tostring()
    noise_exported = 0
    max_attempts = noise_count * 500
    attempts = 0
    fixed_crop_size_mm = 50.0

    # --- 修改：确保噪声文件夹基于基础字体名创建 ---
    # noise_Times_New_Roman (或 noise_Arial 等，取决于 base_noise_font_name)
    noise_base_dir = os.path.join("output", f"noise_{base_noise_font_name}")
    os.makedirs(noise_base_dir, exist_ok=True)

    while noise_exported < noise_count and attempts < max_attempts:
        attempts += 1
        crop_size_mm = fixed_crop_size_mm
        half_crop_mm = crop_size_mm / 2
        min_center_x = margin + safe_margin + half_crop_mm
        max_center_x = width_mm - margin - safe_margin - half_crop_mm
        min_center_y = margin + safe_margin + half_crop_mm
        max_center_y = height_mm - margin - safe_margin - half_crop_mm
        if min_center_x >= max_center_x or min_center_y >= max_center_y:
             print("⚠️  裁剪区域过大，无法生成噪声图像。")
             break
        center_x = random.uniform(min_center_x, max_center_x)
        center_y = random.uniform(min_center_y, max_center_y)
        crop_rect = (center_x - half_crop_mm, center_y - half_crop_mm, crop_size_mm, crop_size_mm)
        crop_area = crop_size_mm * crop_size_mm
        total_overlap_area = 0.0
        for square in placed_squares:
            corners = square.get_corners()
            if not corners: continue
            xs, ys = zip(*corners)
            sq_min_x, sq_max_x = min(xs), max(xs)
            sq_min_y, sq_max_y = min(ys), max(ys)
            square_rect = (sq_min_x, sq_min_y, sq_max_x - sq_min_x, sq_max_y - sq_min_y)
            overlap_area = calculate_rectangle_overlap_area(crop_rect, square_rect)
            total_overlap_area += overlap_area
            if total_overlap_area / crop_area > overlap_threshold:
                break
        overlap_ratio = total_overlap_area / crop_area
        if overlap_ratio <= overlap_threshold:
            viewbox_x = center_x - half_crop_mm
            viewbox_y = center_y - half_crop_mm
            viewbox_width = crop_size_mm
            viewbox_height = crop_size_mm
            local_svg_data = full_svg_data.replace(
                f'viewBox="0 0 {width_mm} {height_mm}"',
                f'viewBox="{viewbox_x} {viewbox_y} {viewbox_width} {viewbox_height}"',
                1
            )

            # --- 修改：使用基于基础字体名的噪声文件夹 ---
            png_path = os.path.join(noise_base_dir, f"noise_{int(center_x)}_{int(center_y)}_overlap{int(overlap_ratio*100)}.png")

            try:
                fixed_output_size_px = 60
                png_data = cairosvg.svg2png(
                    bytestring=local_svg_data.encode('utf-8'),
                    output_width=fixed_output_size_px,
                    output_height=fixed_output_size_px
                )
                img = Image.open(io.BytesIO(png_data))
                img.save(png_path)
                print(f"✅ 已保存噪声图像 (重叠 {overlap_ratio*100:.1f}%) 到: {png_path}")
                noise_exported += 1
            except Exception as e:
                print(f"❌ 导出噪声图像失败 (尝试 {attempts}): {e}")

    if attempts >= max_attempts and noise_exported < noise_count:
        print(f"⚠️  为文件生成噪声图像达到最大尝试次数，可能未生成足够的样本 ({noise_exported}/{noise_count})。重叠阈值: {overlap_threshold*100}%。")

def save_svg(dwg, filename):
    svg_filename = os.path.join("output", "svg", filename)
    pdf_filename = os.path.join("output", "pdf", filename.replace('.svg', '.pdf'))
    dwg.saveas(svg_filename)
    print(f"SVG文件已保存为: {svg_filename}")
    cairosvg.svg2pdf(url=svg_filename, write_to=pdf_filename)
    print(f"PDF文件已保存为: {pdf_filename}")

# --- 主程序 ---
total_files = 10000
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    MofNCompleteColumn(),
    TimeRemainingColumn(),
    expand=True,
) as progress:
    main_task = progress.add_task("[green]生成图像文件...", total=total_files)
    for i in range(1, total_files + 1):
        square_count = random.randint(3, 5)
        min_size = 60
        max_size = 120
        generate_digits = True
        filename = f"{i}.svg"
        create_image(filename, square_count=square_count, min_size=min_size, max_size=max_size, generate_digits=generate_digits)
        progress.update(main_task, advance=1)

print("[bold green]所有文件生成完毕![/bold green]")