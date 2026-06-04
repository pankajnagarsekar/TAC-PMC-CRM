/**
 * Client-side Export Utilities for the Analytics Dashboard.
 */

/**
 * Capture an HTML element and download it as a PNG image.
 */
export async function exportChartAsPNG(element: HTMLElement | null, fileName: string) {
  if (!element) return;
  try {
    // Dynamic import to prevent bundler failures if package isn't present
    // @ts-expect-error - dynamic import may not be typed or resolved locally
    const html2canvas = (await import("html2canvas")).default;
    const canvas = await html2canvas(element, {
      useCORS: true,
      allowTaint: true,
      scale: 2,
      backgroundColor: "#ffffff",
    });
    
    const dataUrl = canvas.toDataURL("image/png");
    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = `${fileName}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (err) {
    console.warn("High-fidelity PNG export failed. Triggering browser print fallback.", err);
    window.print();
  }
}

/**
 * Capture an HTML element and wrap it in a PDF document.
 */
export async function exportChartAsPDF(element: HTMLElement | null, title: string, fileName: string) {
  if (!element) return;
  try {
    // @ts-expect-error - dynamic import
    const html2canvas = (await import("html2canvas")).default;
    // @ts-expect-error - dynamic import
    const { jsPDF } = await import("jspdf");

    const canvas = await html2canvas(element, {
      scale: 2,
      useCORS: true,
      backgroundColor: "#ffffff",
    });

    const imgData = canvas.toDataURL("image/png");
    const pdf = new jsPDF("l", "mm", "a4");
    const imgWidth = 280; // A4 page size landscape width is 297mm
    const imgHeight = (canvas.height * imgWidth) / canvas.width;
    const position = 10;

    pdf.setFont("helvetica", "bold");
    pdf.setFontSize(14);
    pdf.text(title, 10, 10);

    pdf.addImage(imgData, "PNG", 10, position + 5, imgWidth - 20, imgHeight);
    pdf.save(`${fileName}.pdf`);
  } catch (err) {
    console.warn("High-fidelity PDF export failed. Triggering browser print fallback.", err);
    window.print();
  }
}

/**
 * Export any tabular/chart data object list as a CSV file.
 */
export function exportChartDataAsCSV(data: Record<string, unknown>[], columns: string[], fileName: string) {
  if (!data || data.length === 0) return;

  try {
    // 1. Create CSV header row
    const headers = columns.join(",");
    
    // 2. Map data rows
    const rows = data.map((item) => {
      return columns.map((col) => {
        const val = item[col];
        if (val === null || val === undefined) return "";
        // Escape quotes
        const valStr = String(val).replace(/"/g, '""');
        return valStr.includes(",") ? `"${valStr}"` : valStr;
      }).join(",");
    });

    // 3. Combine headers and rows
    const csvContent = "\uFEFF" + [headers, ...rows].join("\n"); // Add BOM for Excel compatibility

    // 4. Trigger download
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${fileName}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error("CSV data export failed:", err);
  }
}
