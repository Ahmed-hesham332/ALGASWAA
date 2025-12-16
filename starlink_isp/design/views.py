from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Design
from .forms import DesignForm
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from vouchers.models import VoucherBatch
from .utils import generate_design_preview

@login_required
def design_list(request):
    designs = Design.objects.filter(owner=request.user)
    batches = VoucherBatch.objects.filter(reseller=request.user)

    return render(
        request,
        "dashboard/design/design_list.html",
        {
            "designs": designs,
            "batches": batches,
        }
    )


@login_required
def design_add(request):
    if request.method == "POST":
        form = DesignForm(request.POST, request.FILES)
        if form.is_valid():
            design = form.save(commit=False)
            design.owner = request.user
            design.save()

            design.preview_image.save(
                f"preview_{design.id}.png",
                generate_design_preview(design),
                save=True
            )

            messages.success(request, "تم حفظ التصميم بنجاح")
            return redirect("design:list")
    else:
        form = DesignForm()

    return render(request, "dashboard/design/design_add.html", {"form": form})

@login_required
def design_delete(request, design_id):
    design = get_object_or_404(
        Design,
        id=design_id,
        owner=request.user
    )
    if design.preview_image:
        design.preview_image.delete(save=False)

    if design.background_image and design.background_image.name != "media/designs/backgrounds/card_background.jpg":
        design.background_image.delete(save=False)

    design.delete()   

    messages.success(request, "تم حذف التصميم بنجاح.")
    return redirect("design:list")


@login_required
def download_design_pdf(request, design_id):
    design = Design.objects.get(id=design_id)

    # example: batch selected via GET ?batch=ID
    batch_id = request.GET.get("batch")
    batch = VoucherBatch.objects.get(id=batch_id)

    # Layout params
    try:
        cols = int(request.GET.get("cols", 5))
        rows = int(request.GET.get("rows", 10))
    except ValueError:
        cols = 5
        rows = 10
    
    if cols < 1: cols = 5
    if rows < 1: rows = 10

    vouchers = batch.vouchers.all().order_by("id")

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{design.name}.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    
    page_width, page_height = A4
    
    # Calculate card dimensions
    CARD_W = page_width / cols
    CARD_H = page_height / rows

    COLS = cols
    ROWS = rows
    PER_PAGE = COLS * ROWS

    x_start = 0
    y_start = page_height - CARD_H

    for index, voucher in enumerate(vouchers):
        pos = index % PER_PAGE
        col = pos % COLS
        row = pos // COLS

        x = col * CARD_W
        y = y_start - row * CARD_H

        # Draw background image
        if design.background_image:
            c.drawImage(
                design.background_image.path,
                x, y,
                CARD_W, CARD_H,
                preserveAspectRatio=False,  # Stretch to fit new dimensions
                mask='auto'
            )
        
        card_w_points = CARD_W  # reportlab uses points by default, so CARD_W is already in points
        
        pdf_font_scale = card_w_points / 160.0 # Assuming 160 is the design base width
        
        pdf_font_size = design.serial_font_size * pdf_font_scale
        c.setFont("Helvetica-Bold", pdf_font_size)
        c.setFillColor(design.serial_color)
        
        x_rel = (design.serial_x / 160.0) * CARD_W
        y_rel = (design.serial_y / 113.0) * CARD_H 
        
        x_pos = x + x_rel
        y_pos = (y + CARD_H) - y_rel - pdf_font_size

        c.drawString(x_pos, y_pos, voucher.serial)

        # New page after PER_PAGE
        if (index + 1) % PER_PAGE == 0:
            c.showPage()

    c.save()
    return response
