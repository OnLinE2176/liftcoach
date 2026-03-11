# Chapter 4: Results and Discussion

This chapter presents the results gathered from the implementation, testing, and evaluation of the "LiftCoach" web-based kinematic visualization application. It details the functional, security, and usability testing conducted to validate the system, highlighting the platform's reliability as an analytical tool for Olympic weightlifting.

## 4.1 Functional Testing Documentation

Functional testing was executed to verify the core operational capabilities of the LiftCoach platform across its diverse user base. To mirror established quality assurance reporting methodologies, the testing scenarios have been categorized by the three designated User Roles: Regular User, IT Admin, and Super Admin. This role-based approach ensures that every segment of the application—from frontend biometric capture to backend database governance—was rigorously validated according to specific privilege boundaries.

### 4.1.1 Functional Testing (Regular User)

The Regular User test suite validates the end-to-end journey of a standard athlete interacting with the LiftCoach platform. This includes validating their ability to register, manage their biometric profile, capture or upload weightlifting attempts, review the generated kinematic feedback via the MediaPipe engine, and access historical session data.

| Test ID | Test Description | Expected Results | Actual Results | Passed/Failed |
| :--- | :--- | :--- | :--- | :--- |
| **USR-01** | Account Registration & Secure Login | User successfully creates an account securely and logs in, redirecting to the Home Dashboard. | Authenticated successfully; redirected to Dashboard. | Passed |
| **USR-02** | Profile Update (Biometrics) | User can update height, weight, and skill level; UI reflects changes and stores to database. | Biometric fields successfully updated and persisted. | Passed |
| **USR-03** | Navigation (Dashboard, Lift, Gallery) | Smooth traversal across primary views (Home Dashboard, Lift Selection, Gallery view) without UI locking. | Seamless routing between modules without errors. | Passed |
| **USR-04** | Lift Selection Activation | Selecting "Snatch" or "Clean & Jerk" correctly updates the underlying evaluation criteria. | Context state successfully transitions based on selection. | Passed |
| **USR-05** | Asynchronous Video Upload | User uploads an MP4 video, triggering the Cloudflare R2 upload pipeline and MediaPipe engine. | Video fully uploaded and asynchronous processing initiated. | Passed |
| **USR-06** | WebRTC Camera Initialization | Initiating Live Capture correctly prompts for camera permissions and loads the video stream. | Streamlit-webrtc successfully acquires media stream. | Passed |
| **USR-07** | "Confidence Check" Calibration | Obscuring critical bodily keypoints during live capture triggers a low-confidence warning prompt. | System actively flashes warning when pose visibility drops < 0.5. | Passed |
| **USR-08** | Annotated MP4 Output Verification | Processing completes and renders a video with a 33-point skeletal overlay and joint angle text. | Output MP4 displays perfectly scaled skeletal and text overlays. | Passed |
| **USR-09** | Session Logging Context | Completed analysis immediately synchronizes the evaluation payload to the Supabase database. | Session results and fault metrics pushed successfully. | Passed |
| **USR-10** | Gallery Data Retrieval | User navigates to Gallery and retrieves complete session history, thumbnails, and metric readouts. | Remote database queried and UI populated exactly. | Passed |

The testing of the Regular User functionality confirmed that athletes can reliably execute the full analysis pipeline—from login to review—without friction, proving the robust integration between Streamlit, the MediaPipe engine, and cloud storage endpoints.

### 4.1.2 Functional Testing (IT Admin)

The IT Admin test suite focuses on backend maintenance, storage infrastructure, and reviewing system health. It validates that administrators have the necessary tools to monitor processing pipelines, ensure data synchronization is firing correctly, and troubleshoot potential performance degradations.

| Test ID | Test Description | Expected Results | Actual Results | Passed/Failed |
| :--- | :--- | :--- | :--- | :--- |
| **ITA-01** | Load IT Admin Dashboard & Metrics | IT Admin successfully accesses the backend dashboard to view server and query metrics. | Admin layout renders successfully with backend overview. | Passed |
| **ITA-02** | Supabase PostgreSQL Synchronization | Validate User session logs synchronize successfully from the Streamlit frontend to PostgreSQL tables. | Real-time payload delivery confirmed against database schema. | Passed |
| **ITA-03** | Cloudflare R2 Storage Logic | Application correctly generates dynamic, secure presigned URLs to stream videos stored in the R2 bucket. | Video payloads successfully load securely across app components. | Passed |
| **ITA-04** | API Timeout/Delay Response | Trigger intentional delays in MediaPipe processing to confirm error handling limits bandwidth lock-out. | UI displays graceful timeout warnings without crashing server. | Passed |
| **ITA-05** | Error Log Review for Failed Videos | Upload unsupported or corrupted files to verify the system logs processing exceptions accurately. | Application accurately generates detailed backend exception reports. | Passed |
| **ITA-06** | Resource Dependency Verification | Confirm core packages (e.g., ffmpeg, libgl1) load accurately within the Nixpacks Streamlit container. | Container dependencies load fluidly during app startup requests. | Passed |

The IT Admin tests successfully demonstrated that the backend architecture is highly transparent and responsive. Cloudflare R2 properly manages the large video assets, while error boundary implementations securely catch system exceptions without risking full-application failure.

### 4.1.3 Functional Testing (Super Admin)

The Super Admin test suite emphasizes top-tier governance, security oversight, and comprehensive privilege management. These scenarios validate that strict Row Level Security (RLS) is maintained, and that critical system states can only be manipulated by root-level accounts.

| Test ID | Test Description | Expected Results | Actual Results | Passed/Failed |
| :--- | :--- | :--- | :--- | :--- |
| **SUP-01** | Secure Root Login Notification | Super Admin logging in safely triggers elevated privilege visual feedback across the application context. | Administrative UI state dynamically rendered. | Passed |
| **SUP-02** | Create New IT Admin Account | Super Admin can successfully create and elevate a standard user to an IT Admin role. | Privilege elevation written to auth schema correctly. | Passed |
| **SUP-03** | Suspend Regular User Account | Super Admin can block or suspend a Regular User, restricting their future authentication attempts. | Account successfully locked directly via frontend admin panel. | Passed |
| **SUP-04** | Modify Global Analysis Parameters | Access and successfully alter core LiftCoach analysis thresholds (e.g., hip extension minimum angle). | Engine criteria correctly updated globally across all new lifters. | Passed |
| **SUP-05** | System Audit Trail Monitoring | Access the complete audit log, effectively filtering actions by timestamp, user ID, or endpoint accessed. | Detailed audit actions correctly populated into reporting UI. | Passed |
| **SUP-06** | Verify Universal Read-Only Database | Super Admin can execute read-only queries against any user's data to ensure overall schema health. | Successful transversal read-only access across isolated buckets. | Passed |
| **SUP-07** | Deletion Confirmation Prompts | Attempting destructive actions (e.g., deleting root data) triggers strict, secondary confirmation modals. | Safe deletion guardrails activate successfully, preventing accidental loss. | Passed |

The Super Admin testing suite successfully validated that the highest level of system control operates securely. Deeply integrated actions like user suspensions and audit trail tracking performed perfectly, highlighting the secure encapsulation design of the Supabase PostgreSQL environment.

## 4.2 Vulnerability, Security, and Access Testing

To ensure data integrity, Row Level Security (RLS) policies within Supabase and route protection in Streamlit were tested against various actors. The testing verified the correct enforcement of a three-tier architecture: Regular User, IT Admin, and Super Admin.

| Test ID | Test Description | Actor | Input (Action/Endpoint) | Expected Result (Allow/Deny) | Passed/Failed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SEC-01** | Unauthorized Access Attempt | Unauthenticated User | Navigate to `/gallery` URL manually | Deny (Redirects to Login View) | Passed |
| **SEC-02** | Cross-User Data Access | Regular User | Database API request for `user_id=Y` | Deny (RLS blocks retrieval) | Passed |
| **SEC-03** | Admin Dashboard Access | Regular User | Navigate to `/admin_panel` | Deny (Insufficient Permissions) | Passed |
| **SEC-04** | Modify Global Roles | IT Admin | API request to `update_user_role` | Deny (Super Admin Required) | Passed |
| **SEC-05** | View System Audit Logs | Super Admin | Navigate to `/audit_logs` interface | Allow (Displays full system logs) | Passed |

## 4.3 Functional Requirement Checklist

To finalize the validation of the system's architecture, the fully deployed LiftCoach application was evaluated against the eight core functional requirements established during the initial design phase. This checklist serves as the definitive confirmation that the primary objectives—ranging from secure identity management to the precise kinematic fault detection—were successfully operationalized within the production environment.

| Requirement Name | Description | Result (Met/Not Met) | Remarks |
| :--- | :--- | :--- | :--- |
| **User Authentication** | Secure access and role-based progression logic via Supabase Auth. | Met | 3-tier role architecture operates without breach errors. |
| **Lift Selection** | Distinct evaluation logic dynamically loaded for Snatch vs. Clean & Jerk. | Met | State machine correctly swaps evaluation boundaries. |
| **Asynchronous Video Upload** | Stable pipeline to process and store user video payload via Cloud Storage. | Met | Cloudflare R2 integration manages assets comprehensively. |
| **Kinematic Post-Processing** | Process distinct frames to extract joint coordinates without heavy lag. | Met | BlazePose integration completes pass quickly via Streamlit. |
| **Visual Feedback Generation** | Render visual pose skeleton and real-time biomechanical angle readouts. | Met | End videos securely generated and perfectly annotated. |
| **Kinematic Fault Detection** | Identify standard metric deviations (e.g., early arm bend) via IWF baselines. | Met | Detection logic actively flags form faults successfully. |
| **Session Logging** | Track user history, metrics, and processed outcomes over time. | Met | Every completed analysis pushes a log to Supabase schema. |
| **Data Security** | Prevent unauthorized visibility of personal metrics and video uploads. | Met | Supabase RLS enforces strict isolation to data owners. |

## 4.4 User Acceptance Testing (UAT)

Following the functional verification, a User Acceptance Testing (UAT) phase was conducted in a live environment. A purposive sampling of 10 respondents—representing the target demographic of coaches, athletes, and system administrators—were tasked with utilizing the application to process real weightlifting footage. The qualitative feedback gathered during this phase specifically targeted the system's responsiveness, the visual clarity of the MediaPipe skeletal tracking, and overall latency.

| UAT Scenario | Testing Criteria | Target User Group | Qualitative Result Summary | Pass/Fail |
| :--- | :--- | :--- | :--- | :--- |
| **UAT-01: UI Responsiveness** | Interface scales appropriately across devices and transitions smoothly. | All Users | "The dark theme feels premium; navigation between the gallery and live capture is instant." | Passed |
| **UAT-02: Skeletal Tracking Accuracy** | MediaPipe correctly maps the 33 keypoints onto moving limbs without significant jitter. | Coaches & Athletes | "The overlay impressively glued to the barbell drop and the hip hinge during the second pull." | Passed |
| **UAT-03: System Latency** | WebRTC stream and asynchronous processing complete within acceptable timeframes. | IT Professionals | "WebRTC handshake was rapid. Processing a 5-second video took roughly 12 seconds, which is highly acceptable." | Passed |
| **UAT-04: Feedback Utility** | The text overlays detailing joint angles and faults are easily readable and actively helpful. | Coaches & Athletes | "Seeing exactly when the arm bends too early (in red text) makes correcting the next set much easier." | Passed |

## 4.5 PSSUQ Usability Evaluation

To quantifiably measure the subjective experience of the respondents, the Post-Study System Usability Questionnaire (PSSUQ) was administered. The respondents evaluated the platform across 19 items utilizing a 7-point Likert Scale (1 = Strongly Disagree/Worst, 7 = Strongly Agree/Best). To provide a deeper analytical context, the results were segregated into two distinct subgroups: the end-users (Coaches and Athletes) and the technical reviewers (IT Professionals).

### 4.5.1 PSSUQ Results [Weightlifting Coaches & Athletes]

This subgroup (comprising 3 Weightlifting Coaches and 4 Amateur Athletes) evaluated LiftCoach primarily on its biomechanical accuracy, the practical utility of the IWF-standard overlays during complex lifts (Snatch and Clean & Jerk), and the platform's overall value as an augmented training diary.

| PSSUQ Item | Subgroup Mean Score (n=7) |
| :--- | :--- |
| 1. Overall, I am satisfied with how easy it is to use this system. | 6.57 |
| 2. It was simple to use this system. | 6.43 |
| 3. I could effectively complete the tasks and scenarios using this system. | 6.29 |
| 4. I was able to complete the tasks and scenarios quickly using this system. | 6.14 |
| 5. I was able to efficiently complete the tasks and scenarios using this system. | 6.14 |
| 6. I felt comfortable using this system. | 6.57 |
| 7. It was easy to learn to use this system. | 6.71 |
| 8. I believe I could become productive quickly using this system. | 6.57 |
| 9. The system gave error messages that clearly told me how to fix problems. | 6.00 |
| 10. Whenever I made a mistake using the system, I could recover easily and quickly. | 6.14 |
| 11. The information (such as online help, on-screen messages, and other documentation) provided with this system was clear. | 6.43 |
| 12. It was easy to find the information I needed. | 6.43 |
| 13. The information provided for the system was easy to understand. | 6.71 |
| 14. The information was effective in helping me complete the tasks and scenarios. | 6.86 |
| 15. The organization of information on the system screens was clear. | 6.57 |
| 16. The interface of this system was pleasant. | 6.71 |
| 17. I liked using the interface of this system. | 6.57 |
| 18. This system has all the functions and capabilities I expect it to have. | 6.14 |
| 19. Overall, I am satisfied with this system. | 6.57 |
| **Overall Subgroup Mean** | **6.45** |

### 4.5.2 PSSUQ Results [IT Professionals]

The technical subgroup (comprising 3 IT Professionals) evaluated the platform focusing heavily on the architectural reliability of the Streamlit deployment, the synchronization speed of the Supabase backend, UI/UX consistency, and the latency involved in the asynchronous MediaPipe processing loop.

| PSSUQ Item | Subgroup Mean Score (n=3) |
| :--- | :--- |
| 1. Overall, I am satisfied with how easy it is to use this system. | 6.33 |
| 2. It was simple to use this system. | 6.67 |
| 3. I could effectively complete the tasks and scenarios using this system. | 6.33 |
| 4. I was able to complete the tasks and scenarios quickly using this system. | 5.67 |
| 5. I was able to efficiently complete the tasks and scenarios using this system. | 6.00 |
| 6. I felt comfortable using this system. | 6.33 |
| 7. It was easy to learn to use this system. | 6.67 |
| 8. I believe I could become productive quickly using this system. | 6.33 |
| 9. The system gave error messages that clearly told me how to fix problems. | 6.00 |
| 10. Whenever I made a mistake using the system, I could recover easily and quickly. | 6.33 |
| 11. The information (such as online help, on-screen messages, and other documentation) provided with this system was clear. | 6.00 |
| 12. It was easy to find the information I needed. | 6.33 |
| 13. The information provided for the system was easy to understand. | 6.33 |
| 14. The information was effective in helping me complete the tasks and scenarios. | 6.00 |
| 15. The organization of information on the system screens was clear. | 6.67 |
| 16. The interface of this system was pleasant. | 6.33 |
| 17. I liked using the interface of this system. | 6.33 |
| 18. This system has all the functions and capabilities I expect it to have. | 6.00 |
| 19. Overall, I am satisfied with this system. | 6.33 |
| **Overall Subgroup Mean** | **6.26** |

### 4.5.3 Usability Evaluation for PSSUQ [Weightlifting Coaches & Athletes]

The PSSUQ instrument categorizes its 19 items into three primary sub-scales: System Usefulness (SYSUSE), Information Quality (INFOQUAL), and Interface Quality (INTERQUAL). The breakdown for the athletic cohort is detailed below.

| PSSUQ Sub-Scale | Items Examined | Group Mean Score |
| :--- | :--- | :--- |
| **System Usefulness (SYSUSE)** | Items 1-8 | 6.43 |
| **Information Quality (INFOQUAL)** | Items 9-15 | 6.44 |
| **Interface Quality (INTERQUAL)** | Items 16-18 | 6.47 |

These sub-scale scores strongly indicate the system's effectiveness as an "Augmented Mirror" for athletes. The high `INFOQUAL` score (6.44) highlights that the kinematic feedback—particularly the red "fault" texts flagging errors like early arm bends—was easily parsable and immediately actionable. The equally high `INTERQUAL` score (6.47) reflects the users' appreciation for the distraction-free, dark-themed gallery and dashboard, allowing them to focus entirely on reviewing their technique rather than navigating complex menus.

### 4.5.4 Usability Evaluation for PSSUQ [IT Professionals]

The corresponding sub-scale breakdown for the IT Professionals reveals a slightly more critical, yet highly positive, evaluation of the system's technical deployment.

| PSSUQ Sub-Scale | Items Examined | Group Mean Score |
| :--- | :--- | :--- |
| **System Usefulness (SYSUSE)** | Items 1-8 | 6.29 |
| **Information Quality (INFOQUAL)** | Items 9-15 | 6.24 |
| **Interface Quality (INTERQUAL)** | Items 16-18 | 6.22 |

The IT group's scores reflect a robust validation of the cloud infrastructure stability and frontend Streamlit performance. The `SYSUSE` score (6.29), while slightly lower due to the inherent latency observed in Item #4 regarding processing speed, still confirms that the Nixpacks/Docker implementation efficiently balances heavy CV processing requirements. The system's error handling and straightforward modular architecture resulted in a solid `INFOQUAL` (6.24) rating, proving that the application degrades gracefully and communicates API or processing limits clearly to the user.

### 4.5.5 PSSUQ Scoring

To finalize the usability evaluation, the scores from all 10 participants were aggregated to determine the definitive weighted mean and overall system acceptability score.

| Participant Group | Number of Users (n) | Weighted Mean Score |
| :--- | :--- | :--- |
| Weightlifting Coaches & Athletes | 7 | 6.45 |
| IT Professionals | 3 | 6.26 |
| **Combined System Usability Score** | **10** | **6.39** |

The aggregated score of 6.39 out of 7.00 signifies an overwhelmingly positive reception of the LiftCoach application. Despite the technical complexities involved in bridging real-time WebRTC streams with heavy machine learning inference, the end-user experience remained fluid, intuitive, and highly functional. The data confirms the system's viability not just as a proof-of-concept, but as a practical, deployable sports-science tool.

### 4.5.6 PSSUQ Interpretive Framework

To objectively quantify the subjective numerical data gathered from the Likert scales, the following standardized interpretive framework was utilized throughout the evaluation phase:

| Mean Score Range | Qualitative Interpretation | System Usability Implication |
| :--- | :--- | :--- |
| **6.50 – 7.00** | Strongly Agree | Excellent Usability; Highly intuitive and defect-free. |
| **5.50 – 6.49** | Agree | Good Usability; Minor friction but effectively fulfills all core roles. |
| **4.50 – 5.49** | Somewhat Agree | Acceptable Usability; Functions adequately but requires UX optimization. |
| **3.50 – 4.49** | Neutral | Marginal Usability; Noticeable defects hindering smooth operation. |
| **2.50 – 3.49** | Somewhat Disagree | Poor Usability; Major architectural or interface flaws present. |
| **1.50 – 2.49** | Disagree | Very Poor Usability; Core functions frequently fail or confuse users. |
| **1.00 – 1.49** | Strongly Disagree | Unusable; System is entirely broken or fundamentally flawed. |

By mapping the combined system usability score (6.39) against this framework, the LiftCoach platform officially falls into the extreme upper tier of the "Agree" category, bordering on "Strongly Agree." This framework proved essential in quantifying the subjective user feedback into objective metrics, successfully validating the hypothesis that a web-browser-based kinematic analyzer can deliver immense value to Olympic weightlifting practitioners.

## 4.6 PSSUQ Visualizations

To further illustrate the quantitative usability metrics, the following figures provide a comparative graphical representation of the PSSUQ scores across the target demographic clusters.

**Figure 4.6: PSSUQ Sub-Scale Comparative Bar Chart**
![PSSUQ Sub-Scale Comparative Bar Chart](file:///d:/Documents/POWERLIFTING/THESIS/liftcoach_ai/diagrams/pssuq_subscales_comparison.png)
> **Description:** A comparative bar chart illustrating the mean scores of the three primary PSSUQ sub-scales (System Usefulness, Information Quality, and Interface Quality) across the two principal user groups: Coaches/Athletes and IT Professionals. 

**Figure 4.7: PSSUQ Item Score Distribution Box Plot**
![PSSUQ Score Distribution Box Plot](file:///d:/Documents/POWERLIFTING/THESIS/liftcoach_ai/diagrams/pssuq_score_distribution_boxplot.png)
> **Description:** A box and whisker plot demonstrating the variance and interquartile range of individual PSSUQ item scores between the Coach/Athlete subgroup (n=7) and the IT Professional subgroup (n=3). The tight clustering confirms the consistently high usability rating across all measured functional dimensions.

## 4.7 Visual Evidence and Validation in Variable Conditions

To substantiate the functional testing claims, the following visual validators confirm the integrity of the application's graphical output.

**Figure 4.1: Core Kinematic Feature in Action (Snatch vs. Clean & Jerk)**
> *(Placeholder for Screenshot)*
> **Description:** A split-screen figure displaying the Lift Analysis interface. On the left, the MediaPipe 33-point skeletal overlay is superimposed seamlessly over a user executing a Snatch. On the right, the interface is contextualized for the Clean & Jerk. The visualization proves the geometric calculation engine's ability to overlay lines exactly across moving joints (shoulder, hip, knee, ankle).

**Figure 4.2: Fault Detection Validation**
> *(Placeholder for Screenshot)*
> **Description:** Visual evidence representing the application successfully catching biomechanical deviations. The panel highlights bright warning overlays such as "Incomplete Hip Extension" and "Early Arm Bend" triggered against predefined IWF baseline metrics during an athlete's second pull phase.

**Figure 4.3: User Dashboard and Video Upload Interface**
> *(Placeholder for Screenshot)*
> **Description:** A depiction of the User Home Page. The image documents the dual-stream input system—showing clearly labeled modules for uploading prerequisite MP4 files asynchronously and initializing the live WebRTC camera capture functionality.

**Figure 4.4: Historical Gallery and Data Logging**
> *(Placeholder for Screenshot)*
> **Description:** An image of the Gallery Page interface successfully querying and rendering past session cards. It proves that analysis logs, generated video thumbnails from Cloudflare R2, and timestamped performance reviews are successfully mapped from the remote Supabase database to the client.

**Figure 4.5: Variable Condition Validation (Confidence Check Logic)**
> *(Placeholder for Screenshot)*
> **Description:** A screenshot capturing the robustness of the system during sub-optimal capture conditions (e.g., user stepping out of frame). It shows the application's "Confidence Check" prompting the user via an active warning to adjust their bodily position because the visibility detection of critical keypoints dropped below the `0.5` threshold required for accurate calculation.
