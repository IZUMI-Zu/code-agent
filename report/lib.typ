// ----------------------------------------------------------------------
// Configuration & Utilities
// ----------------------------------------------------------------------
#let link-color = rgb("#000000") // A more professional "Academic Blue"
#let muted-color = luma(100)     // Darker grey for better readability
#let block-bg-color = luma(248)  // Very light grey for code blocks

// Helper for muted text
#let text-muted(it) = {text(fill: muted-color, it)}

// ----------------------------------------------------------------------
// Main Template Function
// ----------------------------------------------------------------------
#let kunskap(
    // Metadata (API UNCHANGED)
    title: [Title],
    author: "Anonymous", 
    header: "", 
    date: datetime.today().display("[month repr:long] [day padding:zero], [year repr:full]"),

    // Paper size
    paper-size: "a4",

    // Fonts (Optimized for English)
    body-font: ("Linux Libertine", "Times New Roman", "Noto Serif"),
    body-font-size: 11pt, 
    raw-font: ("Hack Nerd Font", "Fira Code", "Consolas", "Monospace"),
    raw-font-size: 9pt,
    headings-font: ("Inter", "Helvetica Neue", "Arial", "Source Sans Pro"),

    // Colors
    link-color: link-color,
    muted-color: muted-color,
    block-bg-color: block-bg-color,

    // The main document body
    body
) = {
    // 1. Page Setup
    set page(
        paper: paper-size,
        margin: (x: 1.5cm, y: 1.8cm), // Adjusted for electronic reading
        // Header is simple: Course name/Header on left
        header: context {
             if counter(page).get().first() > 1 {
                set text(font: headings-font, size: 9pt, fill: muted-color)
                align(left, header)
                v(-5pt)
                line(length: 100%, stroke: 0.5pt + luma(200))
            }
        },
        // Footer: Page number centered
        footer: context {
            set text(font: headings-font, size: 9pt, fill: muted-color)
            align(center, counter(page).display("1 / 1"))
        }
    )

    // 2. Metadata & Document Settings
    set document(title: title, author: if type(author) == array { author.join(", ") } else { author })
    set text(font: body-font, size: body-font-size, lang: "en") // Force English context
    
    // 3. Heading Styling (Clean & Modern)
    set heading(numbering: "1.1") // Enable numbering like "1. Introduction"
    show heading: it => {
        set text(font: headings-font, weight: "bold", fill: rgb("#1a1a1a"))
        
        // Spacing
        if it.level == 1 { v(1.5em) } else { v(1em) }
        
        // Display number and text
        block([
            #if it.numbering != none {
                text(fill: link-color)[#counter(heading).display()]
                h(0.5em)
            }
            #it.body
        ])
        
        v(0.5em, weak: true)
    }

    // 4. Paragraph & Text Settings
    set par(leading: 0.8em, spacing: 1.2em, justify: true, first-line-indent: 0em) // English reports often don't indent if there is spacing

    // 5. List Styling
    set list(indent: 1.5em, marker: ([•], [--]))
    set enum(indent: 1.5em, numbering: "1.")

    // 6. Code Block Styling (Elegant Box)
    show raw.where(block: true): block.with(
        inset: 12pt,
        radius: 3pt,
        width: 100%,
        fill: block-bg-color,
        stroke: 0.5pt + luma(220) // Subtle border
    )
    show raw.where(block: false): box.with(
        inset: (x: 3pt, y: 0pt),
        outset: (y: 2pt),
        fill: block-bg-color,
        radius: 2pt
    )
    show raw: set text(font: raw-font)

    // 7. Link Styling
    show link: set text(fill: link-color)

    // ===================================================================
    // TITLE BLOCK (The "Elegant" Part)
    // ===================================================================
    
    // No pagebreak, everything flows
    {
        set align(center)
        
        // Optional Header/Course info at very top
        if header != "" {
            text(font: headings-font, fill: muted-color, size: 0.9em, weight: "bold", header)
            v(0.8em)
        }

        // Main Title
        text(font: headings-font, size: 24pt, weight: "black", fill: rgb("#1a1a1a"), title)
        v(1em)

        // Authors (Group Members)
        // This handles multiple authors elegantly using a grid layout
        if type(author) == array {
            grid(
                columns: (auto,) * author.len(),
                gutter: 2.5em,
                ..author.map(a => align(center, text(font: body-font, size: 12pt, weight: "medium", a)))
            )
        } else {
            text(font: body-font, size: 12pt, weight: "medium", author)
        }
        
        v(0.8em)
        
        // Date
        if date != none {
            text(font: body-font, fill: muted-color, style: "italic", date)
        }

        v(1.5em)
        
        // Professional Separator Line
        line(length: 100%, stroke: 0.5pt + luma(180))
        v(2em)
    }

    // ===================================================================
    // CONTENT
    // ===================================================================
    
    // Reset alignment for body
    set align(left)
    
    body
}