# 🚨 Master Bulk Extraction Audit Log

This document logs extraction anomalies across the entire corpus of machine-generated PDFs.

### ✅ _[1/32]_ `project 1_less10doors.pdf`
> **Yield:** 9 Doors, 46 HW Items - **No Anomaly Detected**

### 📄 _[2/32]_ `Project 2 _lessthan10doors(1).pdf`
> **Yield:** 0 Doors, 0 HW Items
- 🛑 **Complete Drop:** Zero doors AND Zero hardware extracted (Page classification failure or strictly vector-only).

### ✅ _[3/32]_ `project 3_lessthan10door.pdf`
> **Yield:** 2 Doors, 3 HW Items - **No Anomaly Detected**

### 📄 _[4/32]_ `project4_lessthan10door.pdf`
> **Yield:** 0 Doors, 8 HW Items
- ⚠️ **Zero Drop (Doors):** Hardware was extracted, but ZERO doors found.

### 📄 _[5/32]_ `project5_lessthan10door.pdf`
> **Yield:** 5 Doors, 10 HW Items
- 👻 **Hardware Orphan Bleed:** `5` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[6/32]_ `project7_lessthan10door_outlier.pdf`
> **Yield:** 12 Doors, 29 HW Items
- 📏 **Missing Dimensions:** `12` doors isolated without explicit width attributes.
- 👻 **Hardware Orphan Bleed:** `4` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[7/32]_ `A.820 - Door Schedule.pdf`
> **Yield:** 30 Doors, 6 HW Items
- 👻 **Hardware Orphan Bleed:** `22` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[8/32]_ `Door Schedule.pdf`
> **Yield:** 38 Doors, 0 HW Items
- ⚠️ **Zero Drop (Hardware):** Doors were extracted, but ZERO hardware found.

### 📄 _[9/32]_ `Door Schedule.pdf`
> **Yield:** 18 Doors, 65 HW Items
- 👻 **Hardware Orphan Bleed:** `2` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[10/32]_ `Door Schedule.pdf`
> **Yield:** 5 Doors, 0 HW Items
- ⚠️ **Zero Drop (Hardware):** Doors were extracted, but ZERO hardware found.
- 📏 **Missing Dimensions:** `5` doors isolated without explicit width attributes.

### 📄 _[11/32]_ `209-A4.2-Schedules Notes and Details REV 1.pdf`
> **Yield:** 0 Doors, 0 HW Items
- 🛑 **Complete Drop:** Zero doors AND Zero hardware extracted (Page classification failure or strictly vector-only).

### 📄 _[12/32]_ `A0.03 - DOOR AND WINDOW SCHEDULE, _ HARDWARE.pdf`
> **Yield:** 0 Doors, 0 HW Items
- 🛑 **Complete Drop:** Zero doors AND Zero hardware extracted (Page classification failure or strictly vector-only).

### 📄 _[13/32]_ `049 A600 DOOR SCHEDULE ELEVATIONS & DETAILS.pdf`
> **Yield:** 0 Doors, 0 HW Items
- 🛑 **Complete Drop:** Zero doors AND Zero hardware extracted (Page classification failure or strictly vector-only).

### 📄 _[14/32]_ `A611 - Door Schedule.pdf`
> **Yield:** 0 Doors, 31 HW Items
- ⚠️ **Zero Drop (Doors):** Hardware was extracted, but ZERO doors found.

### 📄 _[15/32]_ `A501 Door and Hardware Schedule.pdf`
> **Yield:** 0 Doors, 0 HW Items
- 🛑 **Complete Drop:** Zero doors AND Zero hardware extracted (Page classification failure or strictly vector-only).

### 📄 _[16/32]_ `A-611 Door Schedule.pdf`
> **Yield:** 17 Doors, 31 HW Items
- 👻 **Hardware Orphan Bleed:** `7` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[17/32]_ `A-220 Door Schedule.pdf`
> **Yield:** 14 Doors, 13 HW Items
- 👻 **Hardware Orphan Bleed:** `1` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[18/32]_ `A600 - Door Schedule.pdf`
> **Yield:** 0 Doors, 5 HW Items
- ⚠️ **Zero Drop (Doors):** Hardware was extracted, but ZERO doors found.

### 📄 _[19/32]_ `A0.30 Door and Hardware Schedule (Addendum 5).pdf`
> **Yield:** 47 Doors, 25 HW Items
- 👻 **Hardware Orphan Bleed:** `21` doors reference a Hardware Set that violates the Extracted Glossary.

### ✅ _[20/32]_ `A62-01 - Door Schedule.pdf`
> **Yield:** 8 Doors, 31 HW Items - **No Anomaly Detected**

### 📄 _[21/32]_ `A5.1 - Door Schedule.pdf`
> **Yield:** 11 Doors, 12 HW Items
- 👻 **Hardware Orphan Bleed:** `8` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[22/32]_ `A8.0 - Door Schedule.pdf`
> **Yield:** 0 Doors, 28 HW Items
- ⚠️ **Zero Drop (Doors):** Hardware was extracted, but ZERO doors found.

### 📄 _[23/32]_ `A602 - Door Schedule.pdf`
> **Yield:** 6 Doors, 17 HW Items
- 👻 **Hardware Orphan Bleed:** `1` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[24/32]_ `A610 - Door Schedule.pdf`
> **Yield:** 21 Doors, 54 HW Items
- 👻 **Hardware Orphan Bleed:** `15` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[25/32]_ `ID-601 Door Schedule.pdf`
> **Yield:** 11 Doors, 6 HW Items
- 👻 **Hardware Orphan Bleed:** `6` doors reference a Hardware Set that violates the Extracted Glossary.

### 📄 _[26/32]_ `A6.10 - Door Schedule.pdf`
> **Yield:** 43 Doors, 0 HW Items
- ⚠️ **Zero Drop (Hardware):** Doors were extracted, but ZERO hardware found.

### 📄 _[27/32]_ `A8.0 - Door Schedule.pdf`
> **Yield:** 37 Doors, 0 HW Items
- ⚠️ **Zero Drop (Hardware):** Doors were extracted, but ZERO hardware found.

### ✅ _[28/32]_ `Door Schedule.pdf`
> **Yield:** 5 Doors, 31 HW Items - **No Anomaly Detected**

### 📄 _[29/32]_ `Door Schedule.pdf`
> **Yield:** 3 Doors, 0 HW Items
- ⚠️ **Zero Drop (Hardware):** Doors were extracted, but ZERO hardware found.

### ✅ _[30/32]_ `Door Schedule and Hardware Set.pdf`
> **Yield:** 45 Doors, 34 HW Items - **No Anomaly Detected**

### 📄 _[31/32]_ `A5.20-DOOR-SCHEDULE,-DETAILS-_-WINDOW-DETAILS-Rev.0.pdf`
> **Yield:** 0 Doors, 0 HW Items
- 🛑 **Complete Drop:** Zero doors AND Zero hardware extracted (Page classification failure or strictly vector-only).

### 📄 _[32/32]_ `Door Schedule.pdf`
> **Yield:** 7 Doors, 15 HW Items
- 👻 **Hardware Orphan Bleed:** `7` doors reference a Hardware Set that violates the Extracted Glossary.
