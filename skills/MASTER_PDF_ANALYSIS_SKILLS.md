# 🏛️ Master Architectural PDF Analysis & Skills

This document is a consolidated library of deep-dive analyses across 26 distinct architectural door schedule formats.
It serves as the ultimate reference for AI agents and human developers to understand structural variations, edge cases, and hardware blending anomalies found in construction documents.

---

## 📄 PDF Source: 049 A600 DOOR SCHEDULE ELEVATIONS & DETAILS

### Analysis for 049 A600 DOOR SCHEDULE ELEVATIONS & DETAILS.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 8933

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, given the filename "049 A600 DOOR SCHEDULE ELEVATIONS & DETAILS.pdf". The presence of "ELEVATIONS & DETAILS" suggests that it may also contain architectural drawings or technical specifications related to doors.

2. **Data Format**: The data is likely in a **bordered table** format. The high number of explicit lines/borders (8933) and rectangles (1226) detected by pdfplumber suggests the presence of tables with defined borders. This, combined with the document type, implies a structured table format.

3. **Headers/Key Fields**: Although the text snippet is not provided, typical door schedule headers might include "Door Number", "Location", "Size", "Type", "Frame", "Hardware", and other relevant details. Without the text snippet, it's challenging to determine the exact headers, but these are common fields found in door schedules.

4. **Unique Visual/Structural Elements**: The presence of a large number of explicit lines/borders and rectangles may indicate the use of **merged cells** or **complex table structures**. Additionally, the inclusion of "ELEVATIONS & DETAILS" in the filename suggests that the document might contain **technical drawings or diagrams**, which could include rotated text, symbols, or other unique visual elements.

5. **Challenges for LLM+RAG Extraction Pipeline**: The pipeline may face challenges due to the following:
* **Complex table structures**: The high number of borders and rectangles might lead to difficulties in accurately identifying and extracting data from the tables.
* **Mixed content**: The presence of both tabular data and technical drawings/diagrams could require the pipeline to handle different types of content and formats.
* **Rotated text or symbols**: If present, rotated text or symbols could pose challenges for OCR (Optical Character Recognition) and text extraction algorithms.
* **Merged cells or irregular table layouts**: These elements might require specialized handling to ensure accurate data extraction and representation.


---

## 📄 PDF Source: 209-A4.2-Schedules Notes and Details REV 1

### Analysis for 209-A4.2-Schedules Notes and Details REV 1.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 5379

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This appears to be a **Door Schedule** document, which is a type of architectural or construction document that outlines the details of doors, including their type, size, hardware, and other relevant information.

2. **Data Format**: The data is presented in a mix of **bordered tables** and **key-value pairs**. The presence of explicit lines/borders (5379) and rectangles (101) suggests that the document contains tables with borders. However, some sections of the text also appear to be in a key-value pair format, where a label or key is followed by a corresponding value.

3. **Headers or Key Fields**: Some of the headers or key fields present in the document include:
	* DOOR SCHEDULE
	* HARDWARE SET
	* DOOR FRAME FINISH COLOR
	* ROOM NAME
	* DOOR TYPE
	* HAND WIDTH
	* HEIGHT
	* THICKNESS
	* MATERIAL
	* FINISH
	* HINGE STOP

4. **Unique Visual or Structural Elements**: The document appears to contain some unique visual or structural elements, including:
	* **Merged cells**: Some cells in the tables seem to be merged, as indicated by the presence of multiple values or labels in a single cell.
	* **Rotated text**: There is no clear evidence of rotated text in the provided snippet, but it's possible that some text may be rotated in other parts of the document.
	* **Outlier formats**: Some sections of the text appear to be in a non-standard format, with unusual spacing or punctuation.

5. **Challenges for LLM+RAG Extraction Pipeline**: The extraction pipeline may face the following challenges with this specific format:
	* **Table detection and parsing**: The presence of bordered tables and key-value pairs may require the pipeline to use a combination of table detection and parsing techniques to accurately extract the data.
	* **Handling merged cells and rotated text**: The pipeline may need to be able to handle merged cells and rotated text, which can make it difficult to accurately extract the data.
	* **Dealing with outlier formats**: The pipeline may need to be able to handle non-standard formats and unusual spacing or punctuation, which can make it difficult to accurately extract the data.
	* **Extracting relevant information**: The pipeline may need to be able to extract relevant information from the document, such as door types, sizes, and hardware, while ignoring irrelevant information.


---

## 📄 PDF Source: A-220 Door Schedule

### Analysis for A-220 Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 4404

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that lists and describes the doors in a building, including their materials, sizes, and hardware.

2. **Data Format**: The data is presented in a mix of **bordered tables** and **key-value pairs**. The presence of explicit lines/borders (4404) and rectangles (471) suggests that there are tables with borders. However, the text format also indicates the use of key-value pairs, particularly in the notes and specifications sections.

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* Door type and material (e.g., SOLID CORE DOOR, HOLLOW METAL DOOR)
	* Door size and configuration (e.g., 3' - 0", 2'-0")
	* Hardware and manufacturer information (e.g., HAGER, PERFECT PRODUCTS)
	* Finish and notes (e.g., SATIN CHROME, US26D #652)
	* Set number, item, quantity, manufacturer, model number, and finish (in the table-like section)

4. **Unique Visual/Structural Elements**: The document contains some unique visual and structural elements, including:
	* Merged cells or sections with multiple lines of text
	* Rotated text or symbols (e.g., "0 - '7")
	* Outlier formats, such as the use of quotation marks and parentheses to group information
	* Tables with multiple columns and rows, but without clear borders or separation between sections

5. **Challenges for LLM+RAG Extraction Pipeline**: The extraction pipeline may face challenges due to:
	* The mix of bordered tables and key-value pairs, which can make it difficult to identify and extract relevant information
	* The presence of merged cells, rotated text, and outlier formats, which can complicate the parsing and interpretation of the text
	* The use of abbreviations and acronyms (e.g., HC, SC, SG, PG), which may require additional processing to resolve
	* The need to handle tables with multiple columns and rows, while also accounting for the lack of clear borders or separation between sections.


---

## 📄 PDF Source: A-611 Door Schedule

### Analysis for A-611 Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 15837

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that lists and describes the doors in a building, including their types, sizes, hardware, and other relevant details.

2. **Data Format**: The data in this document is presented in a **bordered table** format, with explicit lines and rectangles detected by pdfplumber. The text is organized into rows and columns, with clear headers and consistent formatting.

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* DOOR TYPES
	* DOOR SCHEDULE
	* DOOR HARDWARE
	* PANEL W (width)
	* PANEL H (height)
	* TYPE
	* HW SET (hardware set)
	* NOTES

4. **Unique Visual/Structural Elements**: Some unique visual and structural elements in this document include:
	* Merged cells: Some cells appear to span multiple columns, such as the "NOTES" column.
	* Rotated text: None detected.
	* Outlier formats: Some rows have additional text or notes that are not part of the standard table format.

5. **Challenges for LLM+RAG Extraction Pipeline**: The challenges that an LLM+RAG extraction pipeline might face with this specific format include:
	* **Table structure variability**: The table structure is not entirely consistent, with some rows having additional columns or merged cells.
	* **Header detection**: The headers are not always clearly defined, and some rows may have multiple headers or sub-headers.
	* **Data formatting inconsistencies**: The data formatting is generally consistent, but there may be some inconsistencies in the formatting of certain rows or columns.
	* **Contextual understanding**: The pipeline may need to understand the context of the document, including the relationships between different doors, hardware, and other elements, to accurately extract and interpret the data.


---

## 📄 PDF Source: A.820 - Door Schedule

### Analysis for A.820 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 2924

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that lists and describes the doors in a building, including their sizes, materials, and other relevant details.

2. **Data Format**: The data is presented in a **bordered table** format, with explicit lines and rectangles detected by pdfplumber. The presence of 2924 explicit lines/borders and 106 explicit rectangles suggests a structured table layout.

3. **Headers or Key Fields**: The headers or key fields present in the document include:
	* ROOM NAME
	* FINIS NOTES
	* R NO. (Room Number)
	* GROUP
	* RATING
	* PAIR WIDTH
	* HEIGHT
	* TYPE
	* THK (Thickness)
	* MATERIAL
	* FINISH
	* WIDTH
	* HEIGHT (again, possibly referring to a different component)
	* MATERIAL (again, possibly referring to a different component)
	* TYPE (again, possibly referring to a different component)
	* H ( possibly a code or identifier)

4. **Unique Visual or Structural Elements**: The document appears to have some unique visual elements, such as:
	* Merged cells or columns (e.g., the "ROOM NAME" and "FINIS NOTES" columns seem to be merged)
	* Rotated text is not evident, but there may be some text alignment issues or irregularities
	* Outlier formats, such as the use of abbreviations (e.g., "ALUM/GLASS", "WD PL.5") and codes (e.g., "R NO.", "GROUP")

5. **Challenges for LLM+RAG Extraction Pipeline**: The pipeline may face challenges with:
	* Handling merged cells or columns, which can make it difficult to accurately extract data
	* Dealing with abbreviations and codes, which may require additional processing or lookup tables to resolve
	* Extracting data from tables with irregular or inconsistent formatting
	* Handling potential text alignment issues or irregularities, which can affect the accuracy of text extraction
	* Identifying and handling the different types of data present in the document (e.g., door dimensions, materials, ratings) and extracting them correctly.


---

## 📄 PDF Source: A0.03 - DOOR AND WINDOW SCHEDULE, _ HARDWARE

### Analysis for A0.03 - DOOR AND WINDOW SCHEDULE, _ HARDWARE.pdf

#### Structural Info
- Pages: 1
- Tabular: No (or borderless/complex)
- Explicit Borders (Lines): 0

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a "Door and Window Schedule" with a focus on hardware, suggesting it's related to architectural or construction planning.

2. **Data Format**: Given the absence of explicit lines, borders, or rectangles, and without a visible table structure in the text snippet, the data is likely presented in a **free text** or **key-value pairs** format. The lack of detected tables by pdfplumber further supports this inference.

3. **Headers/Key Fields**: Without a clear table structure or a provided text snippet, it's challenging to definitively identify headers or key fields. However, in a door and window schedule, typical headers might include "Door/Window ID," "Type," "Size," "Hardware," "Location," etc.

4. **Unique Visual/Structural Elements**: The absence of explicit lines, borders, or rectangles suggests a simple, possibly unstructured layout. Without more specific details from the text snippet, it's difficult to identify any unique visual elements such as merged cells, rotated text, or outlier formats. The document might rely on whitespace, indentation, or simple text formatting to organize information.

5. **Challenges for LLM+RAG Extraction Pipeline**: 
    - **Lack of Structure**: The free text or key-value pair format without clear boundaries or tables can make it difficult for the pipeline to accurately identify and extract relevant data points.
    - **Variability in Formatting**: The pipeline might face challenges in handling variability in how data is presented, such as inconsistent use of whitespace, indentation, or formatting to denote different types of information.
    - **Contextual Understanding**: To accurately extract data, the pipeline will need to have a strong contextual understanding of what constitutes a "door and window schedule" and the typical information included in such documents.
    - **Custom Parsing Logic**: The pipeline may require custom parsing logic to handle the specific format of this document, which could add complexity to the extraction process.


---

## 📄 PDF Source: A0.30 Door and Hardware Schedule (Addendum 5)

### Analysis for A0.30 Door and Hardware Schedule (Addendum 5).pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 2509

#### Expert Gen AI Analysis

### Analysis of PDF Layout

#### Document Type:
- **Door and Hardware Schedule**

#### Data Format:
- **Tables**: The presence of multiple tables (14) suggests a structured format.
- **Borders**: Given the high number of explicit lines/borders (2509), it is likely that the data is in bordered tables.

#### Headers or Key Fields Present:
- **Floor Finishes** (e.g., "FLOOR FIN.")
- **Door Types and Descriptions** (e.g., "PREFINISHED RACO", "PAINTED HOLLOW METAL")
- **Quantities** (e.g., "QTY")
- **Descriptions** (e.g., "DESCRIPTION")
- **Catalog Numbers** (e.g., "CATALOG NUMBER")
- **Finishes** (e.g., "FINISH MFR")
- **Hardware Groups** (e.g., "Hardware Group No. 103")

#### Unique Visual or Structural Elements:
- **Merged Cells**: Not explicitly mentioned, but the layout suggests potential merged cells for headers.
- **Rotated Text**: The text "2" and "6" appear to be rotated, likely indicating measurements.
- **Outlier Formats**: Some entries like "GL1 AT INTERIOR DOORS" are formatted differently, possibly as notes or conditions.

#### Challenges for LLM+RAG Extraction Pipeline:
1. **Complex Table Structure**: Multiple tables on a single page can complicate extraction and require robust table parsing techniques.
2. **Rotated Text Handling**: The presence of rotated text may pose challenges in accurate text recognition and layout analysis.
3. **Merged Cells**: Merging cells for headers might lead to misinterpretation if not handled correctly by the pipeline.
4. **Variations in Formatting**: Different formatting styles (e.g., notes, conditions) can introduce variability that needs to be managed.
5. **Borderless vs. Bordered Tables**: The presence of both bordered and possibly borderless tables may require distinguishing between them for accurate data extraction.

This analysis should help in designing an effective LLM+RAG pipeline tailored to the specific structure and content of this PDF document.


---

## 📄 PDF Source: A5.1 - Door Schedule

### Analysis for A5.1 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 6704

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that outlines the specifications and requirements for doors in a building.

2. **Data Format**: The data is presented in a mix of **borderless tables** and **key-value pairs**. The text format suggests that there are tables with columns for "MARK", "TYPE", "DESCRIPTION", "FINISH", and "REMARKS", but the borders are not explicitly defined. Additionally, there are key-value pairs scattered throughout the text, such as "1 All doors shall swing in the direction of exit travel."

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* MARK
	* TYPE
	* DESCRIPTION
	* FINISH
	* REMARKS
	* GENERAL NOTES

4. **Unique Visual/Structural Elements**: Some unique visual or structural elements in this document include:
	* **Merged cells**: Although not explicitly visible in the text snippet, the presence of multiple tables and key-value pairs suggests that there might be merged cells in the original PDF.
	* **Rotated text**: There is no evidence of rotated text in the provided text snippet.
	* **Outlier formats**: The document contains a mix of table-like structures and free-text notes, which could be considered an outlier format.

5. **Challenges for LLM+RAG Extraction Pipeline**: The challenges that an LLM+RAG extraction pipeline might face with this specific format include:
	* **Table detection and parsing**: The borderless tables and mixed data format might make it difficult for the pipeline to accurately detect and parse the tables.
	* **Key-value pair extraction**: The scattered key-value pairs throughout the text might require additional processing to extract and normalize the data.
	* **Handling merged cells and outlier formats**: The pipeline might need to be designed to handle merged cells and outlier formats, such as the mix of table-like structures and free-text notes.
	* **Contextual understanding**: The pipeline might require contextual understanding to accurately extract and interpret the data, especially in cases where the text is ambiguous or relies on external knowledge.


---

## 📄 PDF Source: A5.20-DOOR-SCHEDULE,-DETAILS-_-WINDOW-DETAILS-Rev.0

### Analysis for A5.20-DOOR-SCHEDULE,-DETAILS-_-WINDOW-DETAILS-Rev.0.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 16983

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule** with additional information on window details, given the filename and the presence of multiple tables.

2. **Data Format**: The data is likely in a **bordered table** format. The high number of explicit lines/borders (16983) and rectangles (702) suggests the presence of tables with defined borders, which is consistent with a schedule or table-based layout.

3. **Headers/Key Fields**: Without the actual text snippet, it's challenging to pinpoint specific headers or key fields. However, typical door schedules include headers such as "Door Number," "Location," "Size," "Type," "Frame," "Hardware," and similar. The presence of window details might also include headers related to window specifications.

4. **Unique Visual/Structural Elements**: The large number of explicit lines and rectangles could indicate the use of **merged cells** or **complex table structures**. Without visual inspection, it's also possible that there are **rotated text** elements or **outlier formats** used for specific details like notes or special instructions. The presence of multiple tables (4 detected by pdfplumber) might also imply **nested tables** or **tables with varying structures**.

5. **Challenges for LLM+RAG Extraction Pipeline**:
    - **Complex Table Structures**: The pipeline might face challenges in accurately identifying and parsing the table structures, especially if there are merged cells, nested tables, or tables with non-standard layouts.
    - **Variability in Data Format**: The presence of both door and window details could mean that the pipeline needs to handle different types of data formats or tables within the same document, requiring flexibility and adaptability.
    - **Rotated Text or Outlier Formats**: Any rotated text or unusual formatting might not be recognized correctly, potentially leading to extraction errors or requiring pre-processing steps to normalize the text orientation and format.
    - **High Density of Lines and Rectangles**: While indicative of bordered tables, the high density of lines and rectangles could also lead to false positives in table detection or make it challenging to distinguish between actual table borders and other graphical elements.


---

## 📄 PDF Source: A501 Door and Hardware Schedule

### Analysis for A501 Door and Hardware Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 5555

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door and Hardware Schedule**, which is a type of architectural document that outlines the specifications and details of doors and hardware used in a building.

2. **Data Format**: The data in this document is presented in a mix of **bordered tables** and **key-value pairs**, with some sections resembling a **borderless table**. The high number of explicit lines/borders (5555) and rectangles (24) suggests the presence of tables and other structured elements. The text format, with multiple columns and rows, also supports this assessment.

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* DOOR TYPE
	* DOOR SCHEDULE
	* MOUNTING HEIGHTS DETAIL
	* HARDWARE SCHEDULE
	* SET DESCRIPTION
	* SPECIFICATIONS
	* GENERAL DOOR & HARDWARE NOTES
	* PARTITION TYPE

4. **Unique Visual/Structural Elements**: There are no obvious **merged cells** or **rotated text** in the provided text snippet. However, the presence of multiple tables, rectangles, and lines suggests a complex layout. Some sections, like the "DOOR AND HARDWARE NOTES" and "WATER FOUNTAIN DETAIL", appear to have a more **free-text** or **unstructured** format.

5. **Challenges for LLM+RAG Extraction Pipeline**: The challenges that an LLM+RAG extraction pipeline might face with this specific format include:
	* **Handling multiple tables and layouts**: The pipeline will need to accurately identify and separate the different tables and sections, which may have varying structures and formats.
	* **Dealing with unstructured text**: Some sections, like the "DOOR AND HARDWARE NOTES", may require more advanced natural language processing (NLP) techniques to extract relevant information.
	* **Resolving ambiguous or unclear text**: The pipeline may encounter text that is unclear or ambiguous, such as the "ESEER" and "NOITAERCER" sections, which may require additional context or domain knowledge to accurately interpret.
	* **Handling noise and irrelevant data**: The presence of irrelevant text, such as the "moc.sdeseer.www" and "moc.sdeseer@eseers" sections, may require the pipeline to develop strategies for filtering out noise and focusing on the relevant data.


---

## 📄 PDF Source: A6.10 - Door Schedule

### Analysis for A6.10 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 5567

#### Expert Gen AI Analysis

This appears to be a detailed specification or design document for ADA-compliant restroom doors, likely for a building project. Here's a summary of the key points:

1. Door types and configurations:
   - 16-gauge hollow metal frames (painted)
   - Various door finishes including laminate and painted
   - Insulated with low-e glass

2. Dimensions:
   - Stall door sizes: 7'0" x 3'4", 7'2" x 3'0"
   - Frame depths vary from 16 GA to 20 GA

3. Door hardware:
   - Interior push plates
   - Exterior pull handles

4. Applications:
   - Wrap-around wall assemblies
   - Inset in masonry openings

5. Materials and finishes:
   - Wilsonart laminate (Mercer Oak)
   - Painted finish
   - Insulating glass with tempered low-e coating

6. ADA compliance requirements:
   - Door opening clearances
   - Frame depths to accommodate various wall thicknesses

7. Manufacturer specifications:
   - Specific dimensions and tolerances per manufacturer's guidelines

This document appears to be a technical specification for the design and installation of accessible restroom doors, likely prepared by an architect or building designer for use in construction documents. The detailed nature suggests this is part of a larger project plan.


---

## 📄 PDF Source: A600 - Door Schedule

### Analysis for A600 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 1222

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that outlines the specifications and details of doors in a building project.

2. **Data Format**: The data in this document is presented in a combination of **borderless tables** and **free text**. The presence of multiple tables detected by pdfplumber and the high number of explicit lines/borders suggest a structured format, but the text sample shows that the data is not strictly confined to bordered tables. Instead, it uses a mix of tabular data, bullet points, and free-form text to convey information.

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* WINDOW TYPE
	* DOOR TYPE
	* SCALE
	* SPECIFICATIONS
	* COMCHECK FOR GLAZING
	* DOOR / HARDWARE NOTES
	* Door dimensions (e.g., 3'-0" x 7'-0")

4. **Unique Visual/Structural Elements**: This document features:
	* **Merged cells**: Although not explicitly visible in the text sample, the presence of multiple tables and explicit lines/borders suggests that some cells might be merged to accommodate complex data.
	* **Rotated text**: None apparent in the text sample.
	* **Outlier formats**: The use of asterisks (\*) to create a visual separator between different sections of the document is an unusual formatting choice.

5. **Challenges for LLM+RAG Extraction Pipeline**: This specific format may pose the following challenges:
	* **Table detection and parsing**: The combination of borderless tables and free text may make it difficult for the pipeline to accurately detect and parse the tables.
	* **Data normalization**: The varying formats and structures used to present data (e.g., tabular, bullet points, free text) may require additional processing to normalize the data for extraction.
	* **Handling of merged cells and complex layouts**: If the document contains merged cells or complex layouts, the pipeline may struggle to accurately extract data from these areas.
	* **Dealing with outlier formats and special characters**: The use of asterisks (\*) as visual separators may require special handling to avoid misinterpreting them as part of the data.


---

## 📄 PDF Source: A602 - Door Schedule

### Analysis for A602 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 640

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that lists and describes the doors and their associated hardware, frames, and other relevant details for a building project.

2. **Data Format**: The data in this document is primarily presented in a **bordered table** format, with explicit lines and rectangles detected by pdfplumber. The tables contain structured information about doors, frames, and hardware, with clear headers and columns.

3. **Headers or Key Fields**: The headers or key fields present in this document include:
	* Door Type
	* Door Material
	* Door Finish
	* Frame Material
	* Frame Finish
	* Comments
	* Dimensions (e.g., width, height)
	* Room Name
	* Door Number

4. **Unique Visual or Structural Elements**: Some unique visual or structural elements in this document include:
	* A mix of table formats, with some tables having merged cells or rotated text.
	* The presence of abbreviations and codes (e.g., "SCWD" for "SOLID CORE WOOD DOOR") that may require a dictionary or legend to decipher.
	* A section with general notes and project information, which may contain important context for the door schedule.

5. **Challenges for LLM+RAG Extraction Pipeline**: Some potential challenges for an LLM+RAG extraction pipeline working with this document include:
	* Handling the variety of table formats and structures, which may require flexible table detection and parsing algorithms.
	* Resolving abbreviations and codes, which may require a comprehensive dictionary or machine learning-based approach to decode.
	* Extracting relevant information from the general notes and project information sections, which may require natural language processing (NLP) techniques to identify key phrases and context.
	* Dealing with potential errors or inconsistencies in the document, such as missing or duplicate information, which may require data validation and cleaning steps.


---

## 📄 PDF Source: A610 - Door Schedule

### Analysis for A610 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 13606

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that outlines the details of doors, including their types, sizes, materials, and hardware.

2. **Data Format**: The data in this document is primarily in a **borderless table** format, with some sections resembling **key-value pairs**. The presence of 38 tables detected by pdfplumber and a large number of explicit lines/borders (13606) and rectangles (216) suggests a structured format. However, the text format and lack of clear borders indicate that the tables are likely borderless.

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* DOOR TYPES
	* REF: SCHED
	* HARDWARE SCHEDULE
	* ELUDEHCS ( likely an abbreviation for "Electrolynx Hardware")
	* SET: (followed by a number, possibly indicating a set or package of hardware)
	* Door and frame details (e.g., 1X6 TONGUE AND GROOVE WOOD SIDING)
	* Hardware items (e.g., HINGE, FULL MORTISE, DEADLOCK)

4. **Unique Visual/Structural Elements**: Some unique visual or structural elements in this document include:
	* Merged cells or sections with similar formatting
	* Rotated text is not apparent, but some sections have a different text orientation
	* Outlier formats, such as the "SET:" notation followed by a number, which may indicate a specific package or set of hardware

5. **Challenges for LLM+RAG Extraction Pipeline**: The challenges that an LLM+RAG extraction pipeline might face with this specific format include:
	* **Table detection and parsing**: The borderless tables and lack of clear borders may make it difficult for the pipeline to accurately detect and parse the tables.
	* **Key-value pair extraction**: The pipeline may struggle to extract key-value pairs from the document, especially in sections with similar formatting.
	* **Contextual understanding**: The pipeline may need to understand the context of the document, including the abbreviations and notations used (e.g., "ELUDEHCS"), to accurately extract relevant information.
	* **Handling merged cells and sections**: The pipeline may need to handle merged cells or sections with similar formatting to avoid extracting duplicate or incorrect information.


---

## 📄 PDF Source: A611 - Door Schedule

### Analysis for A611 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 11134

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that outlines the specifications and details of doors in a building.

2. **Data Format**: The data in this document is primarily in **free text** format, with some structured information presented in a **borderless table** or key-value pairs. The presence of 16 tables detected by pdfplumber and numerous explicit lines/borders suggests that there may be some tabular data, but the text sample provided does not clearly show a bordered table.

3. **Headers or Key Fields**: Some potential headers or key fields present in the text include:
	* Lock type (e.g., "PULL|PULL", "PUSH PLATE PULL|PUSH")
	* Door hardware descriptions (e.g., "PULL WITH CYLINDER", "LOCK|PUSH BAR")
	* Door type (e.g., "EXIT CYLINDER LOCK", "ENTRY/OFFICE CYLINDER LOCK")
	* Notes and specifications (e.g., "SEE FINISH PLANS FOR PAINT SCHEDULE", "REINFORCE FRAME AT HINGE LOCATIONS")

4. **Unique Visual or Structural Elements**: The text sample shows some unique visual elements, such as:
	* Merged or overlapping text (e.g., "LLOOCCKK // LLAATTCCHH // HHAANNDDLLEE SSEETTSS")
	* Rotated or distorted text (e.g., the text appears to be rotated or skewed in some areas)
	* Outlier formats (e.g., the use of pipes "|" and slashes "/" to separate text)

5. **Challenges for LLM+RAG Extraction Pipeline**: This specific format may pose challenges for an LLM+RAG extraction pipeline due to:
	* The presence of free text and unstructured data, which may require more advanced natural language processing techniques to extract relevant information
	* The use of unique visual elements, such as merged or rotated text, which may require specialized preprocessing or layout analysis techniques
	* The potential for noise or errors in the text data, which may affect the accuracy of the extraction pipeline
	* The need to identify and extract relevant key fields and headers from the text, which may require domain-specific knowledge and expertise.


---

## 📄 PDF Source: A62-01 - Door Schedule

### Analysis for A62-01 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 8249

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that outlines the details of doors, frames, and hardware for a construction project.

2. **Data Format**: The data in this document is primarily in a **borderless table** format, with some sections resembling **key-value pairs**. The presence of numerous explicit lines and rectangles suggests that the document may contain tables, but the text format and lack of clear borders indicate that the tables are likely borderless.

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* DOOR SCHEDULE
	* GENERAL NOTES
	* GENERAL ABBREVIATIONS
	* GLAZING LEGEND
	* NOTES TO GLAZING LEGEND
	* Frame type, window type, and other door-related specifications

4. **Unique Visual/Structural Elements**: This document contains some unique visual and structural elements, including:
	* **Abbreviations**: The document uses a set of abbreviations, which may require special handling during extraction.
	* **Mixed formatting**: The document combines tabular data with free-text notes and legends, which may pose challenges for extraction.
	* **Rotated text**: Although not explicitly visible in the provided snippet, the presence of numerous explicit lines and rectangles suggests that the document may contain rotated text or other non-standard formatting.

5. **Challenges for LLM+RAG Extraction Pipeline**: The specific format of this document may pose the following challenges for an LLM+RAG extraction pipeline:
	* **Handling borderless tables**: The pipeline may struggle to accurately identify and extract data from borderless tables, which may require custom table detection and parsing logic.
	* **Disambiguating abbreviations**: The pipeline may need to be trained to recognize and expand abbreviations used in the document, which can be time-consuming and require significant domain knowledge.
	* **Handling mixed formatting**: The pipeline may need to be able to handle a mix of tabular data, free-text notes, and legends, which can be challenging due to the varying structures and formats.
	* **Robustness to rotated text and non-standard formatting**: The pipeline may need to be designed to handle rotated text, non-standard fonts, and other unique visual elements that may be present in the document.


---

## 📄 PDF Source: A8.0 - Door Schedule

### Analysis for A8.0 - Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 2343

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that outlines the specifications and requirements for doors in a building project.

2. **Data Format**: The data in this document is presented in a combination of **bordered tables** and **key-value pairs**, with some sections featuring **free text**. The presence of explicit lines/borders (2343) and rectangles (126) suggests that the document contains tables with defined borders. The text format, with clear headings and structured information, also indicates the use of tables and key-value pairs.

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* DOOR TYPE
	* DOOR & WINDOW GENERAL NOTES
	* Hardware requirements
	* Code compliance information (e.g., ICC/A117.1)
	* Door frame and material specifications

4. **Unique Visual/Structural Elements**: Some unique visual or structural elements in this document include:
	* Merged cells or sections with multiple columns (e.g., the DOOR TYPE sections)
	* Rotated text is not apparent in the provided snippet, but it's possible that it may be present in other parts of the document
	* Outlier formats, such as the use of quotation marks ("0-'1) and unusual spacing, may indicate the presence of special characters or formatting

5. **Challenges for LLM+RAG Extraction Pipeline**: An LLM+RAG extraction pipeline may face the following challenges with this specific format:
	* **Table detection and parsing**: The presence of multiple tables with varying structures and borders may make it difficult for the pipeline to accurately detect and parse the tables.
	* **Key-value pair extraction**: The use of key-value pairs, especially in the general notes section, may require the pipeline to develop strategies for extracting and structuring this type of data.
	* **Free text analysis**: The presence of free text sections, such as the general notes and code compliance information, may require the pipeline to employ natural language processing (NLP) techniques to extract relevant information.
	* **Special character and formatting handling**: The pipeline may need to develop strategies for handling special characters, such as quotation marks, and unusual formatting, such as the use of multiple spaces or line breaks.


---

## 📄 PDF Source: Door Schedule and Hardware Set

### Analysis for Door Schedule and Hardware Set.pdf

#### Structural Info
- Pages: 2
- Tabular: Yes
- Explicit Borders (Lines): 7470

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule and Hardware Set**, which is a type of architectural document that outlines the specifications and requirements for doors and hardware in a building project.

2. **Data Format**: The data in this document is primarily in a **borderless table** format, with some sections resembling **key-value pairs**. The text is organized in a structured manner, with headings and subheadings, but there are no explicit borders or tables detected by pdfplumber. The presence of 7470 explicit lines/borders and 193 explicit rectangles suggests that the document may contain some tabular structures, but they are not immediately apparent.

3. **Headers and Key Fields**: The headers and key fields present in this document include:
	* Door types (e.g., TYPE A, TYPE AA, TYPE D)
	* Door assembly and frame specifications
	* Hardware sets and requirements
	* General notes and project information (e.g., project title, project number, drawn by, checked by)
	* Room names and door schedules

4. **Unique Visual or Structural Elements**: Some unique visual or structural elements in this document include:
	* The use of abbreviations and codes (e.g., "HM" for Hollow Metal, "PTD" for Painted)
	* The presence of rotated text (e.g., the "FO" and "NOITROP" sections)
	* The use of special characters and symbols (e.g., ©, )
	* The inclusion of contact information and company details (e.g., Powers Brown, phone numbers, fax numbers)

5. **Challenges for LLM+RAG Extraction Pipeline**: An LLM+RAG extraction pipeline may face the following challenges with this specific format:
	* **Table detection and structure identification**: The lack of explicit borders and tables may make it difficult for the pipeline to accurately detect and extract data from the document.
	* **Abbreviation and code resolution**: The use of abbreviations and codes may require additional processing steps to resolve and extract the corresponding values.
	* **Rotated text and special characters**: The presence of rotated text and special characters may require specialized handling to ensure accurate extraction and processing.
	* **Noise and irrelevant data**: The document contains some noise and irrelevant data (e.g., the "FO" and "NOITROP" sections), which may need to be filtered out or ignored during the extraction process.


---

## 📄 PDF Source: Door Schedule

### Analysis for Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 4066

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This appears to be a **Door Schedule** document, which is a type of architectural drawing that lists and describes the doors in a building, including their locations, sizes, and other relevant details.

2. **Data Format**: The data seems to be in a **bordered table** format, given the high number of explicit lines/borders (4066) and rectangles (277) detected by pdfplumber. The text format also suggests a structured table layout.

3. **Headers/Key Fields**: The headers or key fields present in this document likely include:
   - Door Type
   - Door Number
   - Location
   - Size
   - Fire Rating
   - Hardware Set
   - Other door attributes (e.g., frame type, material)

4. **Unique Visual/Structural Elements**: There might be **merged cells** or **rotated text** present, given the complexity of the document and the variety of information being conveyed. However, without a visual representation, it's difficult to confirm. The presence of explicit rectangles and lines suggests a structured format, but the exact layout and any unique elements can only be confirmed by viewing the PDF directly.

5. **Challenges for LLM+RAG Extraction Pipeline**:
   - **Complex Table Structures**: The pipeline might face challenges in accurately identifying and parsing the table structures, especially if there are merged cells, rotated text, or other complex layout elements.
   - **Variability in Data Formats**: Door schedules can vary significantly in their format and content, which might require the pipeline to be highly adaptable or to have been trained on a diverse set of door schedule documents.
   - **Symbolic and Codified Information**: The presence of codes (e.g., "(cid:50)(cid:48)(cid:50)(cid:53)") and abbreviations (likely related to architectural or construction standards) could pose a challenge for the pipeline to correctly interpret and extract meaningful data.
   - **Highly Specialized Vocabulary**: The use of specialized terms and jargon from the architecture and construction industries might require the pipeline to have a comprehensive understanding of these domains to accurately extract and interpret the data.


---

## 📄 PDF Source: ID-601 Door Schedule

### Analysis for ID-601 Door Schedule.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 2517

#### Expert Gen AI Analysis

### Analysis of the Provided PDF Metadata and Text Snippet:

1. **Type of Document:**
   - The document is a **Door Schedule**.

2. **Data Layout:**
   - **Tables:** There are multiple tables present, as indicated by the 17 tables detected.
   - **Lines/Borders/Rectangles:** With 2517 explicit lines/borders and 142 explicit rectangles, it suggests that the document has a complex layout with numerous borders and sections.
   - **Text Format:** The text is primarily in free text format but interspersed with structured data.

3. **Headers or Key Fields:**
   - **General Headers:**
     - DOOR NOTES
     - FRAMELESS GLASS
     - FRAME NOTES
     - SCHEDULED WIDTH
     - SCHEDULED 2 EQUAL (V.I.F.)
     - SCHEDULED 4 EQUAL (V.I.F.)
     - SCHEDULE DOOR
   - **Data Headers:**
     - DOOR + FRAME SCHEDULE
       - NUMBER
       - ROOM NAME
       - WIDTH
       - HEIGHT
       - TYPE
       - FINISH
       - TYPE
       - FINISH
       - HARDWARE
       - COMMENTS

4. **Unique Visual or Structural Elements:**
   - The document contains multiple tables, which are not merged but have distinct sections.
   - There is a mix of free text and structured data within the tables.
   - Some text appears to be rotated (e.g., "THGIEH DELUDEHCS SCHEDULED WIDTH").
   - The headers and notes sections do not follow a consistent format, making it harder to parse.

5. **Challenges for LLM+RAG Extraction Pipeline:**
   - **Complex Layout:** The presence of multiple tables with varying structures can confuse the extraction pipeline.
   - **Rotated Text:** Rotated text (e.g., "THGIEH DELUDEHCS SCHEDULED WIDTH") may require additional preprocessing steps to correctly identify and extract information.
   - **Mixed Data Formats:** Free text mixed with structured data requires robust parsing techniques to distinguish between different types of content accurately.
   - **Non-Standard Headers:** The headers are not consistently formatted, which can lead to misinterpretation by the extraction pipeline.
   - **Merged Cells:** Although no explicit mention of merged cells was noted, the complex layout might imply that some cells are merged, complicating data extraction.

### Summary:
The document is a Door Schedule with a complex layout involving multiple tables and free text. The presence of rotated text and non-standard headers poses challenges for an LLM+RAG extraction pipeline, requiring careful handling to ensure accurate data extraction.


---

## 📄 PDF Source: project 1_less10doors

### Analysis for project 1_less10doors.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 1592

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be a **Door Schedule**, which is a type of architectural document that outlines the details of doors in a building, including their location, size, materials, and hardware.

2. **Data Format**: The data is presented in a mix of **bordered tables** and **key-value pairs**. The presence of explicit lines/borders (1592) and rectangles (27) suggests that the data is organized in a tabular format, but there are also sections with key-value pairs, such as the "HARDWARE SET" sections.

3. **Headers/Key Fields**: The headers or key fields present in the document include:
	* DOOR NUMBER
	* ROOM NAME
	* WIDTH
	* HEIGHT
	* MATERIALS
	* DOOR FRAME
	* COMMENTS
	* HARDWARE SET NO.
	* HARDWARE LIST

4. **Unique Visual/Structural Elements**: The document features some unique visual elements, such as:
	* **Rotated text**: Some text, like "MUNIMULA" and "LATEM", appears to be rotated or distorted, which may indicate a scanned or OCR-generated document.
	* **Merged cells**: Some cells in the tables seem to be merged, as indicated by the presence of multiple values in a single cell (e.g., "6'-0" 7' - 0"").
	* **Outlier formats**: The document contains some unusual formatting, such as the use of "ROOD" and "TES" as headers, which may be errors or artifacts from the scanning/OCR process.

5. **Challenges for LLM+RAG Extraction Pipeline**: The extraction pipeline may face challenges due to:
	* **Noisy or distorted text**: The presence of rotated or distorted text may affect the accuracy of OCR and subsequent text processing.
	* **Complex table structures**: The mix of bordered tables and key-value pairs, along with merged cells and outlier formats, may require specialized table parsing and normalization techniques.
	* **Domain-specific terminology**: The document uses specialized architectural and hardware-related terms, which may require domain-specific knowledge and dictionaries to accurately extract and interpret the data.


---

## 📄 PDF Source: Project 2 _lessthan10doors(1)

### Analysis for Project 2 _lessthan10doors(1).pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 2288

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Type of document**: This appears to be a **Mixed** document, containing multiple schedules, including a Window Schedule, Finish Schedule, Hardware Schedule, and Door Schedule, which are commonly found in architectural or construction plans.

2. **Data format**: The data is primarily in **bordered tables**, as indicated by the high number of explicit lines/borders (2288) and the structured format of the text. However, there are also sections with **key-value pairs** (e.g., "Project No.", "Date Issue", "Scale") and **free text** (e.g., notes, remarks).

3. **Headers or key fields**: The headers or key fields present in the schedules include:
	* WINDOW SCHEDULE: WINDOW #, SIZE (WxH), HEAD HEIGHT, MATERIAL, TYPE, FINISH, GLAZING, REMARKS
	* FINISH SCHEDULE: RM. #, NAME, FLOOR, BASE, PAINTED, TILE, CELING HT., REMARKS
	* DOOR SCHEDULE: DOOR #, LOCATION, SIZE (WxH), HEAD HEIGHT, MATERIAL, FINISH, FRAME, HARDWARE, REMARKS

4. **Unique visual or structural elements**: There are no obvious **merged cells** or **rotated text** in the provided text snippet. However, the presence of multiple schedules, notes, and remarks sections may indicate a complex layout. The text also contains some **outlier formats**, such as the "REVIEWED FOR COMPLIANCE" and "OK TO ISSUE PERMIT" sections, which appear to be free text or annotations.

5. **Challenges for LLM+RAG extraction pipeline**: The pipeline may face challenges due to:
	* **Multiple schedules**: The presence of multiple schedules with different structures and headers may require the pipeline to adapt to different formats and extract relevant information accordingly.
	* **Complex layout**: The combination of bordered tables, key-value pairs, and free text may require the pipeline to handle varying levels of structure and noise in the data.
	* **Outlier formats**: The pipeline may need to handle unusual formats, such as the "REVIEWED FOR COMPLIANCE" section, which may not fit into the standard extraction templates.
	* **Noise and annotations**: The presence of annotations, notes, and remarks may introduce noise in the data, requiring the pipeline to filter out irrelevant information and focus on the relevant data.


---

## 📄 PDF Source: project 3_lessthan10door

### Analysis for project 3_lessthan10door.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 6724

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This appears to be a **Door Schedule** document, which is a type of architectural drawing that outlines the details of doors in a building project. The presence of "DOOR SCHEDULE" in the text and the mention of door types, hardware sets, and door signage support this conclusion.

2. **Data Format**: The data is likely in a **bordered table** format, given the high number of explicit lines/borders (6724) and rectangles (19) detected by pdfplumber. The text sample also shows some structured data, such as the "HARDWARE SET NO." sections and the "DOOR TYPES" section, which suggests a tabular format.

3. **Headers/Key Fields**: The headers or key fields present in this document include:
	* DOOR SCHEDULE
	* HARDWARE SET NO.
	* DOOR TYPES
	* DOOR SIGNAGE
	* INTERIOR DOOR HEAD
	* DATE
	* DESCRIPTION
	* SHEET TITLE
	* SHEET NUMBER
	* PROJECT NUMBER

4. **Unique Visual/Structural Elements**: There are no obvious unique visual or structural elements, such as merged cells or rotated text, in the provided text sample. However, the presence of multiple scales (e.g., "1/4"=1'-0"", "1/2"=1'-0"", "3"=1'-0"") and the use of abbreviations (e.g., "EEFFOC", "KCOR", "KCALB") may indicate some complexity in the document's structure.

5. **Challenges for LLM+RAG Extraction Pipeline**: The pipeline may face challenges due to:
	* The presence of multiple scales and units, which may require special handling to ensure accurate extraction.
	* The use of abbreviations and codes (e.g., "EEFFOC", "KCOR", "KCALB"), which may require a separate dictionary or mapping to resolve.
	* The potential for variations in formatting and structure within the document, which may require the pipeline to be flexible and adaptable.
	* The presence of noise or irrelevant data (e.g., the "CORPORATE" section, which appears to be a company's contact information) that may need to be filtered out during extraction.


---

## 📄 PDF Source: project4_lessthan10door

### Analysis for project4_lessthan10door.pdf

#### Structural Info
- Pages: 1
- Tabular: No (or borderless/complex)
- Explicit Borders (Lines): 0

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: The document is likely a **Door Schedule**, given the filename "project4_lessthan10door.pdf", which suggests a focus on doors in a project with fewer than 10 doors.

2. **Data Format**: The data appears to be in **free text** format, as there are no detected tables, lines, or rectangles. This suggests that the information is presented in a non-tabular, unstructured manner.

3. **Headers/Key Fields**: Without a clear table structure, it's challenging to identify specific headers or key fields. However, common headers in a door schedule might include "Door Number", "Location", "Size", "Type", and "Hardware". These may be present in the text as labels or keywords.

4. **Unique Visual/Structural Elements**: Given the lack of detected lines, rectangles, and tables, it's likely that the document relies on text formatting, such as font styles, sizes, and spacing, to organize and present the information. There may be **merged text blocks** or **custom formatting** used to convey the door schedule details.

5. **Challenges for LLM+RAG Extraction Pipeline**: The free text format and lack of structural elements may pose challenges for an LLM+RAG extraction pipeline, including:
* **Text segmentation**: Identifying the boundaries between different door entries or sections.
* **Entity recognition**: Accurately recognizing and extracting relevant door attributes (e.g., door number, location, size) from the unstructured text.
* **Data normalization**: Standardizing the extracted data into a consistent format, given the potential for varying text formats and descriptions.
* **Contextual understanding**: Correctly interpreting the context and relationships between different pieces of information in the free text format.


---

## 📄 PDF Source: project5_lessthan10door

### Analysis for project5_lessthan10door.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 2048

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This document appears to be an **Architectural Drawing**, specifically a door schedule and hardware set, given the presence of door frame details, partition legends, and hardware schedules.

2. **Data Format**: The data is presented in a mix of **bordered tables** and **key-value pairs**. The presence of explicit lines/borders (2048) and rectangles (112) suggests the use of tables, while the text format indicates key-value pairs, especially in the notes and legends sections.

3. **Headers/Key Fields**: The headers or key fields present include:
   - Door/frame details (e.g., size, type, material, finish)
   - Hardware schedules (e.g., hinges, locksets, door stops)
   - Partition types and legends
   - General notes and codes (e.g., ADA compliance, finish levels)

4. **Unique Visual/Structural Elements**: 
   - The presence of a **partition legend** with symbols and descriptions.
   - **Rotated text** is not explicitly mentioned but could be inferred from the mixed text orientation in architectural drawings.
   - **Merged cells** or **outlier formats** are not directly observable from the text snippet but could be present in the tables or diagrams not shown.

5. **Challenges for LLM+RAG Extraction Pipeline**:
   - **Mixed data formats**: The combination of bordered tables, key-value pairs, and free text may require the pipeline to adapt to different parsing strategies.
   - **Domain-specific terminology**: The use of architectural and construction terms (e.g., "DUROCK CEMENT BOARD," "LEVEL 4 FINISH") may necessitate a specialized vocabulary or knowledge base for accurate extraction.
   - **Symbolic and graphical elements**: While not directly observable in the text snippet, the presence of diagrams, symbols (as in the partition legend), or other graphical elements in the PDF could pose challenges for text-based extraction methods, requiring additional processing steps or integration with image recognition technologies.


---

## 📄 PDF Source: project7_lessthan10door_outlier

### Analysis for project7_lessthan10door_outlier.pdf

#### Structural Info
- Pages: 1
- Tabular: Yes
- Explicit Borders (Lines): 1803

#### Expert Gen AI Analysis

Based on the provided metadata and text snippet, here's the analysis:

1. **Document Type**: This appears to be a **Door Schedule**, which is a type of document used in architectural and construction projects to detail the specifications of doors, including their type, size, material, and hardware.

2. **Data Format**: The data is presented in a mix of **borderless tables** and **key-value pairs**. The use of repeating headers like "HEAD:", "JAMB:", "SILL:", and "DOOR TYPE:" suggests a tabular structure, but there are no explicit borders. The key-value pairs are used to describe specific attributes of each door, such as "DOOR FINISH:" and "FRAME FINISH:".

3. **Headers/Key Fields**: The headers or key fields present in the document include:
   - "HEAD:"
   - "JAMB:"
   - "SILL:"
   - "DOOR TYPE:"
   - "FRAME TYPE:"
   - "DOOR FINISH:"
   - "FRAME FINISH:"
   - "GLASS TYPE:"
   - "HARDWARE" (which includes various types of door hardware)

4. **Unique Visual or Structural Elements**: 
   - The presence of repeating headers with similar values suggests that the document might be using a template or a standardized format for each door entry.
   - There are mentions of specific hardware items with quantities, indicating a detailed specification of door components.
   - The use of abbreviations and codes (e.g., "US19", "PMK", "SAR") suggests a specialized vocabulary or coding system used in the construction or architectural field.
   - The mention of "BY STOREFRONT" and "BY DOOR RAIL MANUFACTURER" indicates that some components or specifications might be dependent on or provided by specific manufacturers or entities.

5. **Challenges for LLM+RAG Extraction Pipeline**:
   - **Variability in Format**: The mix of borderless tables and key-value pairs, along with the use of specialized vocabulary and codes, might pose challenges for accurately identifying and extracting relevant data.
   - **Ambiguity in Data**: The repetition of similar headers with slightly different values could lead to ambiguity in identifying unique door specifications.
   - **Specialized Vocabulary**: The use of industry-specific abbreviations and codes might require the LLM+RAG pipeline to be trained on or have access to a domain-specific knowledge base to accurately interpret and extract data.
   - **Quantity and Unit Extraction**: Extracting quantities (e.g., "(3 EA.)") and units (e.g., "1/2"") correctly, especially when they are embedded within descriptive text, could be challenging.


---



### ⚠️ Auto-Logged Extraction Anomaly: project4_lessthan10door.pdf (Page 1)
- **Timestamp:** 2026-03-31 00:34:23
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (44x6) ===
| 0                            | 1                            | 2                         | 3                              | 4                              | 5                      |
|:-----------------------------|:-----------------------------|:--------------------------|:-------------------------------|:-------------------------------|:-----------------------|
| GROUP#1)                     |                              | GROUP#5A                  | GROUP#9                        | GROUP#9                        |                        |
|                              |                              | HINGE:                    |                                |                                |                        |
|                      ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 02:36:58
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (37×30) ===
| DOOR SCHEDULE PANEL INFORMATION LOCK FUNCTION HINGES ACCESSORIES DETAILS (REFER  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 100A VE | STIBULE | EXTERIOR | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | 5 | X |  |  |  |  |  | X |  |  | X | X |  | X |  | X | X |  |  |
| 100B LO | BBY | VESTIBULE | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | - |  |  |  |  |  |  |  |  |  | X | X |  | X |  |  |  |  | NO LATCH OR LOCK |
| 101B LO | BBY | PROJECTION/STORAGE | 3' - 0" 7' - 1 | 0" 1 3/4" | 1 | SOLID CORE WOOD FLUSH | HOLLOW METAL |  | 2 | 1 | - |  |  |  | X | X |  |  | 4 |  |  |  |  | X |  |  |  |  |  |
| 102 LO | BBY | BOTT...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 03:32:00
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (37×30) ===
| DOOR SCHEDULE PANEL INFORMATION LOCK FUNCTION HINGES ACCESSORIES DETAILS (REFER  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 100A VE | STIBULE | EXTERIOR | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | 5 | X |  |  |  |  |  | X |  |  | X | X |  | X |  | X | X |  |  |
| 100B LO | BBY | VESTIBULE | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | - |  |  |  |  |  |  |  |  |  | X | X |  | X |  |  |  |  | NO LATCH OR LOCK |
| 101B LO | BBY | PROJECTION/STORAGE | 3' - 0" 7' - 1 | 0" 1 3/4" | 1 | SOLID CORE WOOD FLUSH | HOLLOW METAL |  | 2 | 1 | - |  |  |  | X | X |  |  | 4 |  |  |  |  | X |  |  |  |  |  |
| 102 LO | BBY | BOTT...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 03:35:09
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (37×30) ===
| DOOR SCHEDULE PANEL INFORMATION LOCK FUNCTION HINGES ACCESSORIES DETAILS (REFER  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 100A VE | STIBULE | EXTERIOR | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | 5 | X |  |  |  |  |  | X |  |  | X | X |  | X |  | X | X |  |  |
| 100B LO | BBY | VESTIBULE | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | - |  |  |  |  |  |  |  |  |  | X | X |  | X |  |  |  |  | NO LATCH OR LOCK |
| 101B LO | BBY | PROJECTION/STORAGE | 3' - 0" 7' - 1 | 0" 1 3/4" | 1 | SOLID CORE WOOD FLUSH | HOLLOW METAL |  | 2 | 1 | - |  |  |  | X | X |  |  | 4 |  |  |  |  | X |  |  |  |  |  |
| 102 LO | BBY | BOTT...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule and Hardware Set.pdf (Page 1)
- **Timestamp:** 2026-04-17 10:19:13
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (79×35) ===
|  |  |  |  |  | 4 |  |  |  |  |  |  | 3 |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |
|  | DO | OR TYPES |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2100 Travis St Suite 501 | reet, |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | Houston, Texa 713.224.0456 | s 77002 |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 713.224.0457 | fax |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | www.powersb | rown.com ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule and Hardware Set.pdf (Page 1)
- **Timestamp:** 2026-04-17 10:34:06
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (79×35) ===
|  |  |  |  |  | 4 |  |  |  |  |  |  | 3 |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |
|  | DO | OR TYPES |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2100 Travis St Suite 501 | reet, |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | Houston, Texa 713.224.0456 | s 77002 |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 713.224.0457 | fax |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | www.powersb | rown.com ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule and Hardware Set.pdf (Page 1)
- **Timestamp:** 2026-04-17 10:38:38
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (79×35) ===
|  |  |  |  |  | 4 |  |  |  |  |  |  | 3 |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |
|  | DO | OR TYPES |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2100 Travis St Suite 501 | reet, |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | Houston, Texa 713.224.0456 | s 77002 |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 713.224.0457 | fax |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | www.powersb | rown.com ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: project4_lessthan10door.pdf (Page 1)
- **Timestamp:** 2026-04-17 10:56:33
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (44x6) ===
| 0                            | 1                            | 2                         | 3                              | 4                              | 5                      |
|:-----------------------------|:-----------------------------|:--------------------------|:-------------------------------|:-------------------------------|:-----------------------|
| GROUP#1)                     |                              | GROUP#5A                  | GROUP#9                        | GROUP#9                        |                        |
|                              |                              | HINGE:                    |                                |                                |                        |
|                      ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 11:08:02
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (40x7) ===
| 0               | 1                           | 2                           | 3                           | 4                           | 5                           | 6                   |
|:----------------|:----------------------------|:----------------------------|:----------------------------|:----------------------------|:----------------------------|:--------------------|
|                 | GROUP#1)                    | CROUP BORDO                 | GROUP 5SA                   | CROUP#                      | CROUP#                      |                     |
|                 |                             |                             | DQ x ALUM                   |                             |                             |          ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule and Hardware Set.pdf (Page 1)
- **Timestamp:** 2026-04-17 11:44:55
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (79×35) ===
|  |  |  |  |  | 4 |  |  |  |  |  |  | 3 |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |
|  | DO | OR TYPES |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2100 Travis St Suite 501 | reet, |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | Houston, Texa 713.224.0456 | s 77002 |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 713.224.0457 | fax |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | www.powersb | rown.com ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule and Hardware Set.pdf (Page 2)
- **Timestamp:** 2026-04-17 11:45:31
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (71×18) ===
|  |  | Set: 1.0 |  |  |  |  |  |  | Set: 23.0 |  |  |  |  |  |  | 71 | 3.224.0457 fax |
|  |  | Description: Sg | l - Non Ra | ted - Office - | Interior |  |  |  | Description: Sg | l - Rated - | Conf - Interio | r |  |  |  | ww | w.powersbrown.com |
|  |  | 4 Hinge, F | ull Mortise | TA2714 4-1/ | 2" x 4-1/2" | (NRP) | US26D | MK | 4 Hinge, F | ull Mortise | TA2714 4-1/ | 2" x 4-1/2" (N | RP) US26D MK |  |  |  |  |
|  |  | 1 Entry Lo | ck TSR3 | 8807RL | 626 YA |  |  |  | 1 Passage | Latch | TSR3 8801R | L 626 | P YA | ROJE | CT TITLE |  |  |
|  | D | 1 Door Sto | p 446 | US26D | RO |  |  |  | 1 Conceal | ed Closer | 91N 689 | RF |  |  | FR | ACHT TI |  |
|  |  | 3 Silencer | as req | uired. | RO |  |  |  | 1 Door Sto | p 446 | US26D | RO...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: project4_lessthan10door.pdf (Page 1)
- **Timestamp:** 2026-04-17 11:59:36
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (44x6) ===
| 0                            | 1                            | 2                         | 3                              | 4                              | 5                      |
|:-----------------------------|:-----------------------------|:--------------------------|:-------------------------------|:-------------------------------|:-----------------------|
| GROUP#1)                     |                              | GROUP#5A                  | GROUP#9                        | GROUP#9                        |                        |
|                              |                              | HINGE:                    |                                |                                |                        |
|                      ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: project4_lessthan10door.pdf (Page 1)
- **Timestamp:** 2026-04-17 12:07:46
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (44x6) ===
| 0                            | 1                            | 2                         | 3                              | 4                              | 5                      |
|:-----------------------------|:-----------------------------|:--------------------------|:-------------------------------|:-------------------------------|:-----------------------|
| GROUP#1)                     |                              | GROUP#5A                  | GROUP#9                        | GROUP#9                        |                        |
|                              |                              | HINGE:                    |                                |                                |                        |
|                      ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 12:10:57
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (38×31) ===
| DOOR SCHEDULE PANEL INFORMATION LOCK FUNCTION HINGES ACCESSORIES DETAILS (REFER  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 100B 104 | LOBBY CHECK-IN | VESTIBULE OFFICE | 7' - 0" 3' - 0" | 7' - 10" 7' - 10" | 1 3/4" 1 3/4" | 2 2 | ALUMINUM FRAMED ENTRANCE ALUMINUM FRAMED ENTRANCE | ALUMINUM ALUMINUM |  | 15 15 | 14 7 | - - | X |  |  |  |  |  |  | 4 |  | X | X X |  | X X |  |  |  |  | NO LATCH OR LOCK |
| 105 | OPEN GYM | FAMILY TOILET | 3' - 0" | 7' - 10" | 1 3/4" | 1 | SOLID CORE WOOD FLUSH | HOLLOW METAL |  | 2 | 1 | - |  | X |  |  |  |  |  | 4 |  |  | X |  | X |  |  |  |  |  |
| 111 | OPEN GYM | TANK | 3' - 0" | 5' - 4" | 1 3/4" | 5 | SOLID CORE WOOD FLUSH WITH PLASTIC LAMINATE | HOLLO...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A611 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 12:17:17
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (2×2) ===
| EEXXTTEERRIIOORR DDOOOORR SSCCHHEEDDUULLEE LLOOCCAATTIIOONN OOPPEENNIINNGG SSIIZ | GATHER ARCHITECTURE |
|  | Copyright 2024, GATHER ARCHITECTURE, LLC TEXAS REGISTRATION NUMBER: 24427 RED AR |

=== TABLE (61×32) ===
| EEXXTTEERRIIOORR DDOOOORR SSCCHHEEDDUULLEE |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| MMAARRKK | LLOOCCAATTIIOONN |  | CCOONNFFIIGGUURRAATTIIOONN | OOPPEENNIINNGG SSIIZZEE |  | SSIIDDEELLIIGGHHTT SSIIZZEE |  | FFRRAAMMEE |  |  |  |  |  |  | LLEEAAFF |  |  |  |  |  | HHAARRDDWWAARREE |  |  |  |  |  |  |  |  | FFIIRREE RRAATTIINNGG | CCOOMMMMEENNTTSS |
|  | FFRROOMM | TTOO |  | WWIIDDTTHH | HHEEIIGGHHTT | WWIIDDTTHH | HHEEIIGGHHTT | CCOONNSSTTRRUUCCTTIIOONN | PPRROOFFIILLEE |...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A0.30 Door and Hardware Schedule (Addendum 5).pdf (Page 1)
- **Timestamp:** 2026-04-17 12:22:09
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (50×20) ===
| Data |  |  | Panel |  |  |  |  |  | Frame |  |  | Glazing | Details on A0.35 |  |  | General |  |  |  |
| Mark | № | Room Name | Size |  |  |  |  |  |  | Type |  |  | Sill | Head | Jamb | Fire Rating |  | HDWR | Remarks |
| LEVEL 01 |  |  | Width | Height | THK | Matl | Type | Finish | Matl |  | Finish |  |  |  |  |  |  |  |  |
| 100A | 100 | LOBBY | 6'-0" | 7'-0" | 1 3/4" | ALUM | C | ALUM | ALUM | 003 | ALUM | GL2 | 6/A0.35 | 9/A0.35 | 7/A0.35 |  |  | WC714A | ACCESS CONTROL |
| 100B | 100 | LOBBY | 6'-0" | 7'-0" | 1 3/4" | ALUM | C | ALUM | ALUM | 003 | ALUM | GL1 | 1/A0.35 | 3/A0.35 | 2/A0.35 |  |  | C710AC | ACCESS CONTROL |
| 101 | 101 | PUBLIC RESTROOM | 3'-0" | 7'-0" | 1 3/4" | WD | A | PL-02 | ALUM | 001 | ALUM | -- | 1/A0.35 | 3...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A5.1 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 12:23:24
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (83×37) ===
|  |  |  |  |  |  |  |  | BATT INSULATION, TYP |  | MA | RK | TYPE | WIDTH | HEIG | DOOR HT | TH | I | CK | MATERIAL | FINISH | TYPE | FRAME MATERIAL | ASSEMBLY DETAILS M FINISH LABEL HDWR. SILL JAMB HEAD REMARKS | ARK 1 | TYPE SECTIONAL |  | DES | CRIPTION |  |  |  | FIN | ISH R | EMARKS | DATE: 0 | 7/31/2025 |
|  |  | M | ASONRY |  |  |  |  | SEE WALL TYPES T/ | SL | AB 1 | 01 | A | 6' - 0" | 6' - | 8" | 0' | - | 2" | AL/GL | ANOD | C | AL | ANOD |  | OVERHEAD | MFR'S STAND 1/2 HP SCREW | ARD OP DRIVE | ERATION HAR DOOR OPEN | DW ER, W | ARE EATHERST | RIPPING | P | T |  | JOB NO: DRAWN: | GARLANDTX5050 STAFF |
|  |  |  |  |  |  |  |  | 6" BOX FRAMED HEADER, SEE STRUCTRUAL FASTNER -ADD SEALANT AT |  | 1 1 1 1 | 02 03 04 05 | A A D C | 6' ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 12:23:48
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (40x7) ===
| 0               | 1                           | 2                           | 3                           | 4                           | 5                           | 6                   |
|:----------------|:----------------------------|:----------------------------|:----------------------------|:----------------------------|:----------------------------|:--------------------|
|                 | GROUP#1)                    | CROUP BORDO                 | GROUP 5SA                   | CROUP#                      | CROUP#                      |                     |
|                 |                             |                             | DQ x ALUM                   |                             |                             |          ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 12:28:05
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (37×30) ===
| DOOR SCHEDULE PANEL INFORMATION LOCK FUNCTION HINGES ACCESSORIES DETAILS (REFER  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 100A VE | STIBULE | EXTERIOR | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | 5 | X |  |  |  |  |  | X |  |  | X | X |  | X |  | X | X |  |  |
| 100B LO | BBY | VESTIBULE | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | - |  |  |  |  |  |  |  |  |  | X | X |  | X |  |  |  |  | NO LATCH OR LOCK |
| 101B LO | BBY | PROJECTION/STORAGE | 3' - 0" 7' - 1 | 0" 1 3/4" | 1 | SOLID CORE WOOD FLUSH | HOLLOW METAL |  | 2 | 1 | - |  |  |  | X | X |  |  | 4 |  |  |  |  | X |  |  |  |  |  |
| 102 LO | BBY | BOTT...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule and Hardware Set.pdf (Page 1)
- **Timestamp:** 2026-04-17 12:30:50
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (79×35) ===
|  |  |  |  |  | 4 |  |  |  |  |  |  | 3 |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |
|  | DO | OR TYPES |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2100 Travis St Suite 501 | reet, |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | Houston, Texa 713.224.0456 | s 77002 |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 713.224.0457 | fax |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | www.powersb | rown.com ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule and Hardware Set.pdf (Page 2)
- **Timestamp:** 2026-04-17 12:31:42
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (71×18) ===
|  |  | Set: 1.0 |  |  |  |  |  |  | Set: 23.0 |  |  |  |  |  |  | 71 | 3.224.0457 fax |
|  |  | Description: Sg | l - Non Ra | ted - Office - | Interior |  |  |  | Description: Sg | l - Rated - | Conf - Interio | r |  |  |  | ww | w.powersbrown.com |
|  |  | 4 Hinge, F | ull Mortise | TA2714 4-1/ | 2" x 4-1/2" | (NRP) | US26D | MK | 4 Hinge, F | ull Mortise | TA2714 4-1/ | 2" x 4-1/2" (N | RP) US26D MK |  |  |  |  |
|  |  | 1 Entry Lo | ck TSR3 | 8807RL | 626 YA |  |  |  | 1 Passage | Latch | TSR3 8801R | L 626 | P YA | ROJE | CT TITLE |  |  |
|  | D | 1 Door Sto | p 446 | US26D | RO |  |  |  | 1 Conceal | ed Closer | 91N 689 | RF |  |  | FR | ACHT TI |  |
|  |  | 3 Silencer | as req | uired. | RO |  |  |  | 1 Door Sto | p 446 | US26D | RO...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: project4_lessthan10door.pdf (Page 1)
- **Timestamp:** 2026-04-17 15:57:30
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (44x6) ===
| 0                            | 1                            | 2                         | 3                              | 4                              | 5                      |
|:-----------------------------|:-----------------------------|:--------------------------|:-------------------------------|:-------------------------------|:-----------------------|
| GROUP#1)                     |                              | GROUP#5A                  | GROUP#9                        | GROUP#9                        |                        |
|                              |                              | HINGE:                    |                                |                                |                        |
|                      ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 15:58:12
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (37×30) ===
| DOOR SCHEDULE PANEL INFORMATION LOCK FUNCTION HINGES ACCESSORIES DETAILS (REFER  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 100A VE | STIBULE | EXTERIOR | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | 5 | X |  |  |  |  |  | X |  |  | X | X |  | X |  | X | X |  |  |
| 100B LO | BBY | VESTIBULE | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | - |  |  |  |  |  |  |  |  |  | X | X |  | X |  |  |  |  | NO LATCH OR LOCK |
| 101B LO | BBY | PROJECTION/STORAGE | 3' - 0" 7' - 1 | 0" 1 3/4" | 1 | SOLID CORE WOOD FLUSH | HOLLOW METAL |  | 2 | 1 | - |  |  |  | X | X |  |  | 4 |  |  |  |  | X |  |  |  |  |  |
| 102 LO | BBY | BOTT...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: project4_lessthan10door.pdf (Page 1)
- **Timestamp:** 2026-04-17 16:12:10
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (44x6) ===
| 0                            | 1                            | 2                         | 3                              | 4                              | 5                      |
|:-----------------------------|:-----------------------------|:--------------------------|:-------------------------------|:-------------------------------|:-----------------------|
| GROUP#1)                     |                              | GROUP#5A                  | GROUP#9                        | GROUP#9                        |                        |
|                              |                              | HINGE:                    |                                |                                |                        |
|                      ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 16:16:13
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (38×31) ===
| DOOR SCHEDULE PANEL INFORMATION LOCK FUNCTION HINGES ACCESSORIES DETAILS (REFER  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 100B 104 | LOBBY CHECK-IN | VESTIBULE OFFICE | 7' - 0" 3' - 0" | 7' - 10" 7' - 10" | 1 3/4" 1 3/4" | 2 2 | ALUMINUM FRAMED ENTRANCE ALUMINUM FRAMED ENTRANCE | ALUMINUM ALUMINUM |  | 15 15 | 14 7 | - - | X |  |  |  |  |  |  | 4 |  | X | X X |  | X X |  |  |  |  | NO LATCH OR LOCK |
| 105 | OPEN GYM | FAMILY TOILET | 3' - 0" | 7' - 10" | 1 3/4" | 1 | SOLID CORE WOOD FLUSH | HOLLOW METAL |  | 2 | 1 | - |  | X |  |  |  |  |  | 4 |  |  | X |  | X |  |  |  |  |  |
| 111 | OPEN GYM | TANK | 3' - 0" | 5' - 4" | 1 3/4" | 5 | SOLID CORE WOOD FLUSH WITH PLASTIC LAMINATE | HOLLO...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A611 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 16:22:17
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (2×2) ===
| EEXXTTEERRIIOORR DDOOOORR SSCCHHEEDDUULLEE LLOOCCAATTIIOONN OOPPEENNIINNGG SSIIZ | GATHER ARCHITECTURE |
|  | Copyright 2024, GATHER ARCHITECTURE, LLC TEXAS REGISTRATION NUMBER: 24427 RED AR |

=== TABLE (61×32) ===
| EEXXTTEERRIIOORR DDOOOORR SSCCHHEEDDUULLEE |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| MMAARRKK | LLOOCCAATTIIOONN |  | CCOONNFFIIGGUURRAATTIIOONN | OOPPEENNIINNGG SSIIZZEE |  | SSIIDDEELLIIGGHHTT SSIIZZEE |  | FFRRAAMMEE |  |  |  |  |  |  | LLEEAAFF |  |  |  |  |  | HHAARRDDWWAARREE |  |  |  |  |  |  |  |  | FFIIRREE RRAATTIINNGG | CCOOMMMMEENNTTSS |
|  | FFRROOMM | TTOO |  | WWIIDDTTHH | HHEEIIGGHHTT | WWIIDDTTHH | HHEEIIGGHHTT | CCOONNSSTTRRUUCCTTIIOONN | PPRROOFFIILLEE |...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A0.30 Door and Hardware Schedule (Addendum 5).pdf (Page 1)
- **Timestamp:** 2026-04-17 16:26:14
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (50×20) ===
| Data |  |  | Panel |  |  |  |  |  | Frame |  |  | Glazing | Details on A0.35 |  |  | General |  |  |  |
| Mark | № | Room Name | Size |  |  |  |  |  |  | Type |  |  | Sill | Head | Jamb | Fire Rating |  | HDWR | Remarks |
| LEVEL 01 |  |  | Width | Height | THK | Matl | Type | Finish | Matl |  | Finish |  |  |  |  |  |  |  |  |
| 100A | 100 | LOBBY | 6'-0" | 7'-0" | 1 3/4" | ALUM | C | ALUM | ALUM | 003 | ALUM | GL2 | 6/A0.35 | 9/A0.35 | 7/A0.35 |  |  | WC714A | ACCESS CONTROL |
| 100B | 100 | LOBBY | 6'-0" | 7'-0" | 1 3/4" | ALUM | C | ALUM | ALUM | 003 | ALUM | GL1 | 1/A0.35 | 3/A0.35 | 2/A0.35 |  |  | C710AC | ACCESS CONTROL |
| 101 | 101 | PUBLIC RESTROOM | 3'-0" | 7'-0" | 1 3/4" | WD | A | PL-02 | ALUM | 001 | ALUM | -- | 1/A0.35 | 3...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A5.1 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 16:27:24
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (83×37) ===
|  |  |  |  |  |  |  |  | BATT INSULATION, TYP |  | MA | RK | TYPE | WIDTH | HEIG | DOOR HT | TH | I | CK | MATERIAL | FINISH | TYPE | FRAME MATERIAL | ASSEMBLY DETAILS M FINISH LABEL HDWR. SILL JAMB HEAD REMARKS | ARK 1 | TYPE SECTIONAL |  | DES | CRIPTION |  |  |  | FIN | ISH R | EMARKS | DATE: 0 | 7/31/2025 |
|  |  | M | ASONRY |  |  |  |  | SEE WALL TYPES T/ | SL | AB 1 | 01 | A | 6' - 0" | 6' - | 8" | 0' | - | 2" | AL/GL | ANOD | C | AL | ANOD |  | OVERHEAD | MFR'S STAND 1/2 HP SCREW | ARD OP DRIVE | ERATION HAR DOOR OPEN | DW ER, W | ARE EATHERST | RIPPING | P | T |  | JOB NO: DRAWN: | GARLANDTX5050 STAFF |
|  |  |  |  |  |  |  |  | 6" BOX FRAMED HEADER, SEE STRUCTRUAL FASTNER -ADD SEALANT AT |  | 1 1 1 1 | 02 03 04 05 | A A D C | 6' ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 16:27:47
- **Issue:** Zero `HARDWARE` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: img2table]
=== IMG2TABLE (40x7) ===
| 0               | 1                           | 2                           | 3                           | 4                           | 5                           | 6                   |
|:----------------|:----------------------------|:----------------------------|:----------------------------|:----------------------------|:----------------------------|:--------------------|
|                 | GROUP#1)                    | CROUP BORDO                 | GROUP 5SA                   | CROUP#                      | CROUP#                      |                     |
|                 |                             |                             | DQ x ALUM                   |                             |                             |          ...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: A8.0 - Door Schedule.pdf (Page 1)
- **Timestamp:** 2026-04-17 16:32:21
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (37×30) ===
| DOOR SCHEDULE PANEL INFORMATION LOCK FUNCTION HINGES ACCESSORIES DETAILS (REFER  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| 100A VE | STIBULE | EXTERIOR | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | 5 | X |  |  |  |  |  | X |  |  | X | X |  | X |  | X | X |  |  |
| 100B LO | BBY | VESTIBULE | 7' - 0" 7' - 1 | 0" 1 3/4" | 2 | ALUMINUM FRAMED ENTRANCE | ALUMINUM |  | 15 | 14 | - |  |  |  |  |  |  |  |  |  | X | X |  | X |  |  |  |  | NO LATCH OR LOCK |
| 101B LO | BBY | PROJECTION/STORAGE | 3' - 0" 7' - 1 | 0" 1 3/4" | 1 | SOLID CORE WOOD FLUSH | HOLLOW METAL |  | 2 | 1 | - |  |  |  | X | X |  |  | 4 |  |  |  |  | X |  |  |  |  |  |
| 102 LO | BBY | BOTT...
[TRUNCATED]
```
---


### ⚠️ Auto-Logged Extraction Anomaly: Door Schedule and Hardware Set.pdf (Page 1)
- **Timestamp:** 2026-04-17 16:35:17
- **Issue:** Zero `DOOR` rows extracted despite explicit structural classification.
- **Hypothesis:** LLM failed to parse due to unrecognized block architecture, embedded legends, or JSON hallucination-prevention constraints.
- **Raw Output Hook:**
```text
[Source: pdfplumber_tables]
=== TABLE (79×35) ===
|  |  |  |  |  | 4 |  |  |  |  |  |  | 3 |  |  |  |  | 2 |  |  |  |  |  |  |  |  |  |  |  | 1 |  |  |  |  |  |
|  | DO | OR TYPES |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 2100 Travis St Suite 501 | reet, |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | Houston, Texa 713.224.0456 | s 77002 |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | 713.224.0457 | fax |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | www.powersb | rown.com ...
[TRUNCATED]
```
---
