---
config:
  flowchart:
    layout: dagre
  layout: dagre
---
flowchart TB
    Start["User Starts"] --> Step1["Login to Portal (SSO)"]
    Step1 --> Step2["View CA Recommendations"]
    Step2 --> RecEngine["Recommendation Engine\n(custom questionnaire)"]
    RecEngine --> RecChoice{"Suggested: Public or Private?"}
    RecChoice L_RecChoice_PublicRedirect_0@-- Public --> PublicRedirect["Redirect to Public CA\n(show external link)"]
    RecChoice -- Private --> InternalReco["Recommend Internal CA\n(show internal CA link)"]
    InternalReco --> ForceOption{"Force use of Public CA?"}
    ForceOption -- No --> Step3["Fill Certificate Request Form"]
    ForceOption -- Yes --> ForceReason["Show textbox: Provide reason for forcing public CA"]
    ForceReason --> SendForce["Send request (reason) to approver/system\nLog request & show Public CA link (popup)"]
    SendForce --> PublicRedirect
    Step3 --> Choice1{"Generate or Upload CSR?"}
    Choice1 -- Generate --> Gen["Generate CSR in Portal"]
    Choice1 -- Upload --> Upload["Upload Existing CSR"]
    Gen --> Step4["Review Request Details"]
    Upload --> Step4
    Step4 --> Step5["Submit Request"]
    Step5 --> Backend1["Create Request Record"]
    Backend1 --> DB1[("Save to Database")] & Audit1["Log Request Created"] & Step6["Notify Approver"]
    Step6 --> Choice2{"Approver Decision"}
    Choice2 -- Reject --> Reject["Request Rejected"]
    Choice2 -- Approve --> Approve["Request Approved"]
    Reject --> Notify1["Notify User of Rejection"] & Audit2["Log Rejection"]
    Notify1 --> EndReject["End"]
    Approve --> Audit3["Log Approval"] & Step7["Submit to ADCS Host"]
    Step7 --> ADCS1["ADCS Host Receives"]
    ADCS1 --> ADCS2["Run certreq Command"]
    ADCS2 --> ADCS3["CA Processes Request"]
    ADCS3 --> Choice3{"Status"}
    Choice3 -- Error --> Error1["Handle Error"]
    Choice3 -- Pending --> Poll["Poll for Status"]
    Choice3 -- Success --> Step8["Certificate Issued"]
    Error1 --> Choice4{"Retry?"}
    Choice4 -- Yes --> Step7
    Choice4 -- No --> Notify1
    Poll --> Choice3
    Step8 --> ADCS4["Retrieve Certificate"]
    ADCS4 --> DB2[("Store Certificate")]
    DB2 --> Audit4["Log Certificate Issued"] & Step9["Notify User"]
    Step9 --> Step10["User Downloads Certificate"]
    Step10 --> EndSuccess["End Success"]
    Step10 -.-> Revoke1["User Requests Revocation"]
    Revoke1 --> Revoke2["Process Revocation"]
    Revoke2 --> Revoke3["Submit to ADCS"]
    Revoke3 --> Revoke4["CA Revokes Certificate"]
    Revoke4 --> Revoke5["Update CRL and OCSP"]
    Revoke5 --> Audit5["Log Revocation"] & Notify2["Notify User"]
    Notify2 --> EndRevoke["End"]
    DB2 -.-> Monitor1["Daily Expiry Scan"]
    Monitor1 --> Choice5{"Expiring Soon?"}
    Choice5 -- Yes --> Monitor2["Send Reminder"]
    Choice5 -- No --> Monitor1
    Monitor2 --> Monitor1
     Start:::userClass
     Step1:::userClass
     Step2:::userClass
     RecEngine:::backendClass
     RecChoice:::decisionClass
     PublicRedirect:::userClass
     InternalReco:::backendClass
     ForceOption:::decisionClass
     Step3:::userClass
     ForceReason:::userClass
     SendForce:::backendClass
     Choice1:::decisionClass
     Gen:::userClass
     Upload:::userClass
     Step4:::userClass
     Step5:::userClass
     Backend1:::backendClass
     DB1:::dbClass
     Audit1:::auditClass
     Step6:::backendClass
     Choice2:::decisionClass
     Reject:::errorClass
     Notify1:::errorClass
     Audit2:::auditClass
     EndReject:::endClass
     Audit3:::auditClass
     Step7:::backendClass
     ADCS1:::backendClass
     ADCS2:::backendClass
     ADCS3:::backendClass
     Choice3:::decisionClass
     Error1:::errorClass
     Step8:::backendClass
     Choice4:::decisionClass
     ADCS4:::backendClass
     DB2:::dbClass
     Audit4:::auditClass
     Step9:::backendClass
     Step10:::userClass
     EndSuccess:::endClass
     Revoke1:::userClass
     Revoke2:::backendClass
     Revoke3:::backendClass
     Revoke4:::backendClass
     Revoke5:::backendClass
     Audit5:::auditClass
     Notify2:::backendClass
     EndRevoke:::endClass
     Monitor1:::backendClass
     Choice5:::decisionClass
     Monitor2:::backendClass
    classDef userClass fill:#E3F2FD,stroke:#1976D2,stroke-width:2px
    classDef backendClass fill:#E8F5E9,stroke:#388E3C,stroke-width:2px
    classDef decisionClass fill:#FFF3E0,stroke:#F57C00,stroke-width:2px
    classDef dbClass fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px
    classDef auditClass fill:#ECEFF1,stroke:#455A64,stroke-width:2px
    classDef endClass fill:#C8E6C9,stroke:#2E7D32,stroke-width:3px
    classDef errorClass fill:#FFEBEE,stroke:#C62828,stroke-width:2px
    L_RecChoice_PublicRedirect_0@{ animation: none }
