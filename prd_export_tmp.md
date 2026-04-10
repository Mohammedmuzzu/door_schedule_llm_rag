## **Door Schedule**

The **Door Schedule** is a master reference table listing **all unique doors** in a construction project. ​
It captures each door’s **location, physical characteristics, material specifications, and**
**associated hardware set** (which in turn maps to the Division 8 specification). And skip the
information that is not available with confidence.


This document acts as the **bridge between architectural design information and hardware**
**specifications**, allowing downstream systems (procurement, manufacturing, shipping, installation,
compliance) to reference each door precisely.

#### **Document Overview**


Each record (row) in the Door Schedule represents a **unique door instance**, identifiable by its
**Door Number** . Each door record should be segregated into structured data, irrespective of the
unavailability of the attributes. ​
​ ​ ​ Additional attributes describe the door’s:


●​ **Location Context**   - building level, area, and sometimes room mapping. ​

●​ **Physical Parameters**   - dimensions, frame and slab types, fire rating. ​

●​ **Functional Parameters**   - hardware set, usage remarks, keying info, etc. ​

●​ **Visual/Type Reference**   - DOOR TYPE is any numeric, alphabetic or a combination of both
(e.g., A1, 5, B, C-1, etc.) referring to **door design drawings** also included in the same PDF.


**Reference images from document -**


**All unique Doors, Door types are covered in this Table**


**Door Types are covered here**

#### **Data Structure / Schema Specification**


Below is a **field-by-field definition** of the Door Schedule dataset with data types, field formats,
and relationships.


**Field Name** **Description** **Example** **Data Type** **Constraints /**

**Format**



​


**Source /**
**Relation**


|LEVEL /<br>AREA|Location grouping of<br>doors, indicating fol or or<br>building zone.|Level 1 –<br>Area A|String|Enum-like structured<br>text; may contain<br>hierarchical labels<br>(“Level 2 – Area B”)|Architectural<br>grouping|
|---|---|---|---|---|---|
|**DOOR**<br>**NUMBER**|Unique identifer for<br>each door in the project.|1421A|_String_|Must be unique<br>across project|Primary key|
|**DOOR TYPE**|Reference to door<br>design (defned in<br>drawing sheet within<br>Door Schedule PDF).|A5|_String_|Alphabetic, Numeric<br>orAlphanumeric<br>(A1–A9, B1–B9, etc.)|Maps to<br>door type<br>drawings|
|**FRAME**<br>**TYPE**|Type of door frame<br>material or design.|HM /<br>ALUM /<br>WD|_String_|{HM=Hollow Metal,<br>ALUM=Aluminium,<br>WD=Wood, etc.}|Material<br>classifcation|
|**Frame**<br>**Dimensions**|Height, Width of the<br>frame|3'-0" / 6'-0"|_Numeric_<br>_(Feet,_<br>_Inches,_<br>_Cms, Mts_<br>_etc)_|Standard imperial or<br>Metric format (ft’-in”,<br>cm or m)|Physical<br>dimension|
|**DOOR**<br>**OPENING**<br>**WIDTH**|Clear opening width of<br>door.|3'-0" / 6'-0"|_Numeric_<br>_(Feet,_<br>_Inches,_<br>_Cms, Mts_<br>_etc)_|Standard imperial or<br>Metric format (ft’-in”,<br>cm or m)|Physical<br>dimension|
|**DOOR**<br>**OPENING**<br>**HEIGHT**|Clear opening height.|7'-0"|_Numeric_<br>_(Feet,_<br>_Inches,_<br>_Cms, Mts_<br>_etc)_|Standard imperial or<br>Metric format (ft’-in”,<br>cm or m)|Physical<br>dimension|


|HEAD /<br>JAMB / SILL<br>DETAIL REF|Reference to detail<br>drawings for joinery<br>specifci ations (as per<br>A7.11 or others).|A7.11|String|Optional|Cross-refere<br>nce to<br>architectural<br>drawings|
|---|---|---|---|---|---|
|**FIRE**<br>**RATING**|Fire-resistance rating of<br>door assembly.|45 MIN / 1<br>HR / ----|_String_|Allowed values: {20<br>MIN, 45 MIN, 1 HR, 2<br>HR, ---- (none)}|Compliance<br>attribute|
|**HDWR SET**|Hardware Set reference<br>ID (maps to Division 8<br>specifcation for<br>hardware details).|711C /<br>503S|_String_|Alphanumeric code|Foreign key<br>→ Division 8<br>Spec<br> <br>|
|**KEYED**<br>**NOTES**|Reference to keyed<br>callouts in design<br>documents.|12A / 14|_String_<br>_(Nullable)_|Optional|Design<br>annotation|
|**REMARKS**|Descriptive notes about<br>function, fnish, or<br>operational intent.|“Classroo<br>m function,<br>STC 42”|_String_|Free text|Operational<br>notes|
|**DOOR SLAB**<br>**MATERIAL**<br>**(Derived)**|Derived from Door Type<br>drawing (e.g., Plastic<br>Laminate, Painted<br>Hollow Metal).|Plastic<br>Laminate|_String_|Derived from<br>drawing legend|Dependent<br>on DOOR<br>TYPE|
|**VISION**<br>**PANEL**<br>**(Derived)**|If present, size of glass<br>cutout in door slab.|4"x24"|_String_<br>_(Dimension_<br>_)_|Optional; appears<br>only for<br>glazed/vision panel<br>doors|Derived<br>from<br>drawing|


|GLAZING<br>TYPE<br>(Derived)|Type of glass used if<br>applicable.|Glass Type<br>CT4|Enum<br>(String)|Optional|Derived<br>from<br>drawing|
|---|---|---|---|---|---|
|**FINISH**<br>**(Derived)**|Surface fnish or paint<br>type (door and frame).|STC 42,<br>Painted<br>Metal|_String_|Optional|Derived<br>from door<br>type<br>drawing<br>legend|


## **Division 8 Specification**

The **Division 8 (Openings)** section defines all **hardware sets** used across door types within a
project. ​
Each hardware set (also known as a _Hardware Group_ or _Hardware Set Number_ ) specifies **every**
**component** required to complete the door assembly — including its description, catalog
reference, finish, and manufacturer.


In essence:


●​ **One Hardware Set** = a complete collection of hinges, locks, closers, stops, gaskets, seals,
etc. ​

●​ **Each Door** in the Door Schedule references one of these hardware sets via its **HDWR**
**SET** field. ​

●​ This allows the system to map every door to the exact components and specifications
required for installation. ​

#### **Document Overview**


Each section in the Division 8 document contains:


1. ​ **Hardware Group Header** **​**


○​ **Group Number / Name**      - e.g., _Hardware Group No. 103 – SGL Office Lock_ _​_

○​ **Functional Description**      - summarizing intended use (e.g., _Single Office Door_,
_Exterior Storeroom Door_ ). ​

○​ **Applicable Door Numbers**      - optional list of door numbers referencing this group. ​

2. ​ **Component Table** **​**


○​ Lists all hardware components belonging to that set with fields for: ​


■​ Quantity ​


■​ Unit of Measure (EA, PAIR, SET) ​


■​ Description ​


■​ Catalog Number / Model Code ​


■​ Finish Code (e.g., 626, 630, BK) ​


■​ Manufacturer Abbreviation (e.g., IVE, FAL, LCN, ZER) ​


3. ​ **Notes / Remarks** **​**


○​ Sometimes includes usage clarifications, e.g. _“Use silencers at non-rated doors.”_ _​_

4. ​ **Door Configuration Awareness** **​**


○​ Hardware set already accounts for door configuration: ​


■​ _Single door_ = quantities as listed. ​


■​ _Double door (pair)_ = quantities already adjusted (e.g., 6 hinges, 2 closers). ​


○​ No additional quantity doubling is required when mapping to Door Schedule. ​

#### **Data Structure / Schema Specification**


|Field Name|Description|Example<br>Value|Data<br>Type|Constraints /<br>Format|Notes /<br>Relations|
|---|---|---|---|---|---|
|**HARDWARE SET**<br>**NUMBER**|Unique identifer<br>for each<br>hardware set.|103 / 214|_String_|Must be<br>unique per<br>Division 8<br>document.|Primary Key<br>for this table;<br>Foreign Key<br>from Door<br>Schedule<br>(HDWR SET)|
|**HARDWARE SET**<br>**NAME / FUNCTION**|Functional name<br>of the set or<br>door type<br>application.|SGL Ofce<br>Lock / PR<br>Exterior<br>Storeroom<br>Lock/CLSR|_String_|Free text|Describes<br>intended door<br>usage|
|**APPLICABLE DOOR**<br>**NUMBERS**|Optional list of<br>doors using this<br>set.|1419, 1419A|_Array of_<br>_Strings_|Optional /<br>nullable|Derived from<br>Door<br>Schedule link|
|**QTY**|Quantity of each<br>component in<br>the set.|3 / 6 / 1|_Integer_|Positive<br>integer|Specifes<br>number of<br>units required|
|**UNIT OF MEASURE**|Measurement<br>unit for quantity.|EA / PAIR /<br>SET|_Enum_<br>_(String)_|Allowed<br>values: {EA,<br>PAIR, SET}|Component<br>attribute|
|**COMPONENT**<br>**DESCRIPTION**|Component<br>type / purpose.|HINGE,<br>OFFICE<br>LOCK,<br>SURFACE<br>CLOSER|_String_|Free text|Core<br>hardware<br>component<br>descriptor|
|**CATALOG NUMBER /**<br>**MODEL CODE**|Manufacturer’s<br>product code.|5BB1 4.5 X<br>4.5 / MA521H<br>DN|_String_|Free text|Procurement<br>reference|
|**FINISH CODE**|Finish standard<br>(e.g., ANSI<br>BHMA code).|626 / 630 /<br>BK / AA|_Enum_<br>_(String)_|From<br>standardized<br>fnish codes|Afects<br>aesthetic and<br>durability|


|MANUFACTURER<br>CODE|Abbreviation of<br>manufacturer.|IVE / FAL /<br>LCN / ZER|Enum<br>(String)|Mapped to<br>Manufacturer<br>Master List|Vendor<br>identifei r|
|---|---|---|---|---|---|
|**NOTES / COMMENTS**|Additional<br>instructions or<br>exceptions.|“Use<br>silencers at<br>non-rated<br>doors”|_String_<br>_(nullable)_|Optional|Operational<br>guidance|

## **Relational Model**



**Entity Relation** **Type** **Description**



**Division 8 → Door**
**Schedule**


**Division 8 → Component**
**List**


**Division 8 →**
**Manufacturer Master**

### **Milestone 1-**



One-to-M
any


One-to-M
any


Many-toOne



Each hardware set can be linked to multiple doors via the

**HDWR SET field (foreign key in Door Schedule).**


Each hardware set contains multiple components, each
recorded as a row in the components sub-table.


Each component references a manufacturer from the
Manufacturer Master table.


### **Step 1- Door Schedule × Division 8 Data Integration Model**

##### **Goal**

Build a model that extracts, cleans, and joins data from Door Schedule and Division 8 documents
to produce a unified hardware-set–level aggregate. ​
At the end of this stage, the model should show, for every hardware set:


●​ total number of doors (using that set) ​

●​ split of unit doors vs pair doors ​


●​ total number of door leaves (unit × 1 + pair × 2) ​

●​ total quantity of each hardware components used for each door type and total used for
the project (project-level) ​

##### **Scope**


●​ Accept Door Schedule and Division 8 documents in any format (table-based or
text-based; scanned or digital). ​

●​ Extract relevant fields through parsing + OCR or smilar if needed. ​

●​ Normalize data (field names, keys, formats etc). ​


**●​** Join datasets using Hardware Set ID as the common field. ​

●​ Aggregate outputs by hardware set. ​

●​ Exclude pricing and installation time estimation (this is Milestone 2/3 scope). ​

##### **Model Flow**


**1.** **​** **Extract** **​**


**○​** Door Schedule → Door Number, Door Type (Single/Pair), Hardware

Set ID. ​


**○​** Division 8 → Hardware Set ID, list of components (Description, Quantity,

Finish, Manufacturer etc). ​

**2.** **​** **Clean & Normalize** **​**


**○​** Trim and standardize Hardware Set ID. ​

○​ Convert quantities to numeric; expand abbreviations (e.g., EA → Each). ​


**○​** Detects door type (single or pair) from Door Schedule. **​**

**3.** **​** **Join** **​**


**○​** Join Door Schedule ↔ Division 8 on Hardware Set ID. ​

**4.** **​** **Aggregate** **​**


**○​** For each Hardware Set ID: ​


■​ count of unit doors and pair doors ​


■​ compute door leaves = (unit × 1) + (pair × 2) ​


■​ multiply component quantity (from Division 8) × total doors (using that set) ​

→ gives total quantity per component at project level ​

##### **Final Output (Table Structure)**



**Hardw**
**are Set**

**ID**

##### **Example**



**Hardw**
**are Set**

**Name**



**Door**
**Type**



**Unit**
**Doo**

**rs**



**Pair**
**Doo**

**rs**



**Tota**

**l**
**Doo**

**rs**



**Door**

**Leav**

**es**



**Compon**

**ent**
**Descript**

**ion**



**Catal**

**og**
**No.**



**Fini**

**sh**



**Manufactu**

**rer**



**Qty**

**per**

**Do**

**or**
**(fro**

**m**
**Div**

**8)**



**Total**

**Qty**
**(Proje**

**ct)**



**●​** **Door Schedule:** **​**

**3 doors (D101, D102, D103) → all have Hardware Set 103, each a single door.** **​**

**●​** **Division 8:** **​**

**Hardware Set 103 = 3 hinges, 1 lock, 1 stop.** **​**


**Computation → Final Aggregate**


|Hardware Set<br>ID|Unit<br>Doors|Pair<br>Doors|Door<br>Leaves|Component|Qty per<br>Door|Total Qty<br>(Project)|
|---|---|---|---|---|---|---|
|103|3|0|3|HINGE|3|9|
|103|3|0|3|LOCK|1|3|
|103|3|0|3|DOOR STOP|1|3|

##### **Key Output Expectations**

**●​** **Aggregation should be able to switch between hardware-sets and door types** **​**

**●​** **The model should be robust to PDF format variations (column order, layout, scanned**
**pages).** **​**

**●​** **Output as CSV / JSON for downstream pricing and installation modules.**

#### **Acceptance Criteria**


Model accuracy 99.5%
Model coverage 95%
​

## **Step 2 – Time and Labor Cost Estimation (Installation)**


**Objective**


To extend the merged output (from Door Schedule + Division 8 extraction) by estimating
installation time, total man-hours, and corresponding labor cost for each **Hardware Set Group** .


Once all doors are mapped to their respective hardware sets, the model proceeds to compute
installation effort metrics.


This module performs **four key operations:**


**1. Hardware Set–Level Aggregation**


Determines, for every hardware set, the number of **unit doors**, **pair doors**, and the **quantity of**
**door leaves** .


**Formula:** **​**
quantity_door_leaves = unit_doors × pair_doors


**Example:**


●​ Hardware Set: **HDWR-15.0 (PR)** **​**

●​ unit_doors = 3, pair_doors = 2 ​

●​ quantity_door_leaves = 3 × 2 = 6 ​


**2. Component–Level Aggregation**


For each hardware set, aggregate all hardware components defined in Division 8, calculating the
total quantity of each component that will be installed project-wide. ​
Each component’s quantity (as per Division 8) is multiplied by the **quantity_door_leaves** for that
hardware set, yielding an aggregated component count.


**Example:**


**3. Component–Level Time Mapping**


Associates each component within that hardware set to its corresponding **installation time per**
**unit** (from the Installation Master Sheet). ​
Since component names in Division 8 may vary from the master sheet nomenclature, a
**Component Mapping Model** infers semantic equivalence ​
_(e.g., “NRP Hinge”, “Anchor Hinge”, and “Butt Hinge” → master category “NRP / Butt or Anchor_
_Hinge”)._


**4. Man-Hour and Cost Computation**


Multiplies the **total quantity of each component** (derived above) by its **per-unit installation time**,
sums across all components, and converts the total minutes into hours. ​
These **man-hours** are then multiplied by the **Prevailing Wage Rate** (sourced from the _Log sheet_ )
to yield the final **Labor Cost** for each hardware set.


**5. Add/ Edit new components**


Ability to add new components and edit the existing components along with the time associated
with them


#### **Calculation details, rules**

##### **Input Source**

The **Log Sheet** serves as the primary input for project-level contextual and cost data. ​
It includes:


●​ **Project metadata:** Project name, project number, estimator name, GC name, bid and plan
dates, architect, and specification references. ​

●​ **Project site details:** Job site address and total distance in miles from the primary facility
(Client Address). ​

●​ **Cost parameters:** **​**


○​ _Wage Scale (per hour)_ → e.g., Drywall Hanger, Carpenter ​

○​ _Allowances:_ Gas, Hotel, Meal, and Parking ​

○​ _Additional flags:_ Drug Testing (1/0), Parking (1/0), LEED Material (1/0), Labor Burden,
off-load inventory ​

##### **Computation Overview**


Once the **man-hours** for installation are derived from Step 3, this step computes the **total bid** by
adding contextual costs from the Log sheet.


1. ​ **Base Labor Cost Calculation** **​**


○​ Derived as: ​

total_labor_cost = total_man_hours × wage_scale​


○​ Example: ​
If total man-hours = 601.58 and wage_scale = 23.13 → ​

labor_cost = 601.58 × 23.13 = 13,914.62​


2. ​ **Additional Allowances** **​**

Allowances are conditionally applied based on distance and project configuration


parameters: ​


○​ **Gas Allowance** → added if total_miles > 40​

Per mile cost should be an editable input field​


○​ **Hotel Allowance** → added if stay or outstation project flag = 1
○​ **Meal Allowance** → added if stay or outstation project flag = 1 ​


○​ **Parking Allowance** → added if parking_flag = 1​


○​ **Drug Testing/Background Check Fee** → added if drug_testing = 1​


3. ​ _(Exact conditional logic to be specified in the “Rule Definitions” sub-section below.)_ _​_


4. ​ **Overhead and Profit (Option to edit and change)** **​**


○​ Overhead = 15% of total labor cost ​

○​ Profit = 20% of subtotal (labor + overhead) ​

5. ​ **Equipment and Mobilization Costs (Option to edit and change)** **​**


○​ Includes **off-load/inventory handling**, **tool/mobilization allowances**, and **sales tax**
**on equipment** (e.g., 8.25%) with option to remove sales tax
○​ Off-load for 1st floor doors= no. of doors in 1st level x 25 mins x cost per hour
○​ Off-load for above 1st floor doors= no. of doors above 1st level x 35 mins x cost per
hour
○​ Cost per hour= Total Installation Bid/ Total hours allowed ​

6. ​ **Final Bid Aggregation** **​**

The final bid computation aggregates all subcomponents as shown below:


## **Step 3 - Component Cost Estimation**

##### **Objective**

To compute the **hardware supply cost** at a **per-component, per-door, per-hardware-set** level
by combining:


1.​ **Extracted Quantities** from​


○​ Door Schedule (door count, door type)​

○​ Division 8 (component list & component quantity per door / per leaf)
○​ Component level aggregation - example - in the total data set - total quantity of
this component - across all doors
○​

|Type|Manufac<br>turer|Description|
|---|---|---|
|HINGE|IVE|5BB1HW 4.5 X 4.5 NRP|



2.​ **User-entered Unit Price Inputs** for each unique hardware component.​


The system must aggregate all components across the project and calculate the **total hardware**
**supply cost** based on:​
**Total Quantity (per component) × Unit Price (editable input)** .


This step strictly focuses on **component-level material cost** and excludes installation labor,
overhead, or allowances (covered in other milestones).

# **Scope**


The module must:


●​ Allow the user to **input a price per unit** for every unique hardware component extracted
from Division 8.​

●​ Automatically aggregate:​


○​ Component-level total quantities across all doors​

○​ Total cost per component
○​ Total cost for all components ​

# **Computation Logic**

##### **1. Aggregate Unique Components**


Identify each unique component using a composite key:​
**{Component Description + Catalog Number + Finish + Manufacturer}**

##### **2. Compute Total Quantity (Derived from Step 1)**


Use aggregated quantity from Door Schedule × Division 8 mapping:


total_qty(component) = Σ (qty_per_door_or_leaf ×

number_of_applicable_doors)

##### **3. Apply Unit Price (User Input)**

component_cost = total_qty × unit_price

##### **4. Compute Hardware Set–Level Cost**

hardware_set_cost = Σ (component_cost for all components in that set)

##### **5. Compute Project-Level Total**

project_total_cost = Σ (hardware_set_cost across all sets)

#### Final Output (Structured Table Format)

##### **A. Component-Level Cost Table**


**Hardware**

**Set**



**Component**
**Description**



**Catalog**

**No.**



**Finish** **Manufacturer** **Total**

**Qty**



**Unit Price**

**(Input)**



**Total**

**Cost**


##### **B. Overall Project Summary**

| Total Hardware Supply Cost |

##### **C. Export to a proposal template after uploading the individual component** **costs manually**


-​ Option to add logo of the client along with client details
-​ Option to add notes/ exclusions/ limitations and clarifications to the proposal


