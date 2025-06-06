import os
import json
from io import BytesIO
import textwrap

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Preformatted
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.colors import black, red # Using red as requested

from tqdm import tqdm

from reportlab.pdfbase.pdfmetrics import stringWidth

try:
    from PIL import Image as PILImage, ImageDraw
except ImportError:
    PILImage = None

def create_annotated_pdf(image_folder, annotation_file, output_pdf_path="annotated_images.pdf",
                         max_images=100, image_max_pixel_width=1200, jpeg_quality=80):
    """
    Creates a PDF file with images and their respective annotations,
    displaying each annotation's bounding boxes on a dedicated image instance,
    with custom formatting and optimization.

    Args:
        image_folder (str): Path to the folder containing annotated images.
        annotation_file (str): Path to the JSON file containing annotations.
        output_pdf_path (str): The desired name for the output PDF file.
        max_images (int): The maximum number of images to process. Note: This limit
                          now applies to the number of *annotations* processed, not just unique images.
        image_max_pixel_width (int): Max pixel width for image resizing (if Pillow is used).
                                      Images wider than this will be downsampled.
        jpeg_quality (int): JPEG compression quality (1-100, higher means less compression).
                            Only applies if Pillow is used and image is saved as JPEG.
        bbox_line_color: Color for the bounding box lines (e.g., reportlab.lib.colors.red).
        bbox_line_width (int): Width of the bounding box lines in pixels.
    """
    doc = SimpleDocTemplate(output_pdf_path, pagesize=A4, compression=1)
    styles = getSampleStyleSheet()
    story = []

    annotation_style = styles['Normal']
    annotation_style.fontName = 'Courier'
    annotation_style.fontSize = 9
    annotation_style.textColor = black
    annotation_style.leftIndent = 0.5 * inch
    annotation_style.rightIndent = 0.5 * inch

    try:
        with open(annotation_file, 'r') as f:
            all_annotations_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Annotation file not found at {annotation_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {annotation_file}. Check file format.")
        return

    annotations_to_process = all_annotations_data[:max_images]
    num_annotations_to_process = len(annotations_to_process)

    print(f"Preparing {num_annotations_to_process} annotation entries for PDF (this is the preparation phase)...")
    if PILImage is None:
        tqdm.write("Warning: Pillow not installed. Bounding box plotting and image optimization will be skipped. Install with 'pip install Pillow' for full functionality.")

    available_text_width_points = A4[0] - (1 * inch) - (1 * inch) - annotation_style.leftIndent - annotation_style.rightIndent
    char_width_points = stringWidth('M', annotation_style.fontName, annotation_style.fontSize)
    if char_width_points <= 0:
        max_chars_per_line_estimate = 80
    else:
        max_chars_per_line_estimate = int(available_text_width_points / char_width_points)
    max_chars_per_line_estimate -= 5

    annotation_counter = 0

    for i, annotation_entry in tqdm(enumerate(annotations_to_process), total=num_annotations_to_process, desc="Processing annotations for PDF"):
        annotation_counter += 1
        
        image_filename = os.path.basename(annotation_entry["image_path"])
        image_path = os.path.join(image_folder, image_filename)
        
        if not os.path.exists(image_path):
            tqdm.write(f"Warning: Image file not found at {image_path} for annotation {annotation_counter}. Skipping this annotation.")
            continue

        try:
            if PILImage:
                pil_img = PILImage.open(image_path).convert('RGB')
                
                if "bbox" in annotation_entry and isinstance(annotation_entry["bbox"], list):
                    draw = ImageDraw.Draw(pil_img)
                    # Get the original image dimensions for coordinate transformation
                    original_image_width = pil_img.width
                    original_image_height = pil_img.height

                    for bbox_coords in annotation_entry["bbox"]:
                        if isinstance(bbox_coords, list) and len(bbox_coords) == 4:
                            try:
                                x1_raw, y1_raw, x2_raw, y2_raw = bbox_coords

                                # Convert raw coordinates to integers first
                                x1_int, y1_int, x2_int, y2_int = int(x1_raw), int(y1_raw), int(x2_raw), int(y2_raw)

                                # --- Y-axis Transformation (Bottom-Left Origin to Top-Left Origin) ---
                                # Y increases upwards from bottom-left. Pillow needs Y increasing downwards from top-left.
                                y1_transformed = original_image_height - y1_int
                                y2_transformed = original_image_height - y2_int

                                # --- X-axis (no transformation needed as X increases right from bottom-left) ---
                                # Ensure x1 is always the leftmost, x2 is the rightmost
                                x1_final = min(x1_int, x2_int)
                                x2_final = max(x1_int, x2_int)

                                # Ensure y1 is always the topmost (smallest Y in Pillow's system), y2 is bottommost
                                y1_final = min(y1_transformed, y2_transformed)
                                y2_final = max(y1_transformed, y2_transformed)

                                draw.rectangle(
                                    (x1_final, y1_final, x2_final, y2_final),
                                    outline="red",
                                    width=5
                                )
                            except Exception as bbox_e:
                                tqdm.write(f"Warning: Could not draw bbox {bbox_coords} on {image_filename}. Error: {bbox_e}")
                
                if pil_img.width > image_max_pixel_width:
                    aspect_ratio = pil_img.height / pil_img.width
                    new_height = int(image_max_pixel_width * aspect_ratio)
                    pil_img = pil_img.resize((image_max_pixel_width, new_height), PILImage.LANCZOS)
                
                img_byte_arr = BytesIO()
                pil_img.save(img_byte_arr, format='JPEG', quality=jpeg_quality, optimize=True)
                img_byte_arr.seek(0)
                
                img = Image(img_byte_arr)
            else:
                img = Image(image_path)

            max_width = A4[0] - (2 * inch)
            
            if img.drawWidth > max_width:
                img_scale = max_width / img.drawWidth
                img.drawWidth = max_width
                img.drawHeight = img.drawHeight * img_scale
            
            story.append(img)
            story.append(Spacer(1, 0.2 * inch))

        except Exception as e:
            tqdm.write(f"Warning: Could not process/add image {image_path} (or draw bboxes for annotation {annotation_counter}). Skipping this annotation entry. Error: {e}")
            continue

        story.append(Paragraph(f"<b>Annotation {annotation_counter}:</b>", styles['h2']))

        annotation_raw_text = json.dumps(annotation_entry, indent=2)

        wrapped_json_lines = []
        for line in annotation_raw_text.splitlines():
            leading_spaces = len(line) - len(line.lstrip())
            indent_str = ' ' * leading_spaces
            content_to_wrap = line[leading_spaces:]

            wrap_width_for_content = max_chars_per_line_estimate - leading_spaces
            if wrap_width_for_content <= 0:
                wrap_width_for_content = 10
            
            if len(content_to_wrap) > wrap_width_for_content:
                wrapped_content_parts = textwrap.fill(
                    content_to_wrap,
                    width=wrap_width_for_content,
                    break_on_hyphens=False,
                    subsequent_indent='  '
                )
                wrapped_json_lines.extend([indent_str + part for part in wrapped_content_parts.splitlines()])
            else:
                wrapped_json_lines.append(line)
        
        final_formatted_annotation_text = '\n'.join(wrapped_json_lines)
        story.append(Preformatted(final_formatted_annotation_text, annotation_style))
        story.append(Spacer(1, 0.1 * inch))
        
        if i < num_annotations_to_process - 1:
            story.append(PageBreak())
        else:
            story.append(Spacer(1, 0.5 * inch))

    print("\nStarting final PDF generation. This may take some time depending on content size...")
    try:
        doc.build(story)
        print(f"PDF successfully created at {output_pdf_path}")
    except Exception as e:
        print(f"Error building PDF: {e}")

if __name__ == "__main__":
    IMAGE_DIR = "test_assets/annotated"
    ANNOTATION_FILE = "annotations/annotations.json"
    OUTPUT_PDF = "annotated_data.pdf"

    os.makedirs(IMAGE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(ANNOTATION_FILE), exist_ok=True)

    print("\n--- Starting PDF Generation ---")
    create_annotated_pdf(
        IMAGE_DIR,
        ANNOTATION_FILE,
        OUTPUT_PDF,
        max_images=75,
        image_max_pixel_width=1200,
        jpeg_quality=80
    )
    print("--- PDF Generation Complete ---")