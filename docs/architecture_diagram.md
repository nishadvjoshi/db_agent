# 🏗️ AI-Powered Domain-Driven Data Warehouse Architecture

Here is the comprehensive architecture diagram reflecting the Multi-Agent End-to-End Data Modeling, Engineering, and Semantic Intelligence pipeline. The layout captures the massive 3-phase flow with all 18 autonomous agents.

```mermaid
flowchart TD
    %% Styling and Themes
    classDef default fill:#ffffff,stroke:#cbd5e1,stroke-width:1px,color:#0f172a
    classDef header fill:#f8fafc,stroke:none,color:#0f172a,font-weight:bold
    classDef phaseA fill:#16a34a,stroke:#14532d,stroke-width:2px,color:#ffffff,font-weight:bold
    classDef phaseB fill:#2563eb,stroke:#1e3a8a,stroke-width:2px,color:#ffffff,font-weight:bold
    classDef phaseC fill:#ea580c,stroke:#9a3412,stroke-width:2px,color:#ffffff,font-weight:bold
    classDef artifactBox fill:#f1f5f9,stroke:#94a3b8,stroke-dasharray: 4 4
    classDef agent fill:#ffffff,stroke:#22c55e,stroke-width:2px,color:#0f172a
    classDef agentB fill:#ffffff,stroke:#3b82f6,stroke-width:2px,color:#0f172a
    classDef agentC fill:#ffffff,stroke:#f97316,stroke-width:2px,color:#0f172a
    classDef aws fill:#f8fafc,stroke:#cbd5e1,stroke-width:2px,color:#0f172a

    %% TOP HEADER: User & UI
    User([👤 User / Data Architect / Analyst / Data Engineer])
    UI[💬 Conversational UI & Chat<br/>(Streamlit / React Components)]
    Modeler[📊 Insights & Data Modeler View<br/>(Schema, Lineage, Metrics, Quality)]
    
    User <--> UI
    UI <--> Modeler

    %% =======================
    %% LEFT COLUMN: Data Sources
    %% =======================
    subgraph DataSources [DATA SOURCES]
        direction TB
        Sys[Operational Systems<br/>EHR / EMR, CRM, Billing]
        DBs[Databases<br/>MySQL, PostgreSQL, Oracle]
        Files[Files & APIs<br/>CSV, JSON, REST]
        Stream[Streaming / Events<br/>Kafka, Kinesis]
    end

    %% =======================
    %% PHASE A: STRATEGIC DDD
    %% =======================
    subgraph PhaseA_Wrap [ ]
        direction TB
        TitleA[PHASE A - DOMAIN (STRATEGIC DDD)<br/>Discover, Model & Align the Business Domain]:::phaseA
        
        A1[1. Domain Discovery Agent]:::agent
        A2[2. Bounded Context Agent]:::agent
        A3[3. Ubiquitous Language Agent]:::agent
        A4[4. Context Mapping Agent]:::agent
        A5[5. Aggregate Modeling Agent]:::agent
        A6[6. Domain Event Agent]:::agent
        A7[7. Data Product Agent]:::agent

        A1 --> A2
        A2 --> A3
        A2 --> A4
        A4 --> A5
        A3 --> A6
        A5 --> A6
        A5 --> A7
        A6 --> A7
        
        %% ARTIFACTS A
        subgraph ArtifactsA [PHASE A OUTPUT ARTIFACTS]
            direction LR
            OutA1[(Business<br/>Glossary)]
            OutA2[(Bounded Context<br/>Registry)]
            OutA3[(Context Map<br/>Repository)]
            OutA4[(Domain Event<br/>Catalog)]
            OutA5[(Data Product<br/>Catalog)]
        end
        class ArtifactsA artifactBox
        A7 -.-> ArtifactsA
    end

    %% =======================
    %% PHASE B: ANALYTICAL MODEL
    %% =======================
    subgraph PhaseB_Wrap [ ]
        direction TB
        TitleB[PHASE B - BRIDGE (DOMAIN ➔ ANALYTICAL MODEL)<br/>Translate Domain Concepts Into Analytical Models]:::phaseB
        
        B8[8. Grain & Metrics Agent]:::agentB
        B9[9. Dimensional / Vault Modeling Agent]:::agentB
        B10[10. Logical Model Agent]:::agentB

        subgraph ModelingApproaches [Modeling Approaches]
            direction LR
            Kimball[Dimensional Modeling<br/>(Kimball)<br/>Star/Snowflake Schema]
            Vault[Data Vault Modeling<br/>Hubs, Links, Satellites]
        end

        B8 --> B9
        B9 --> B10
        B9 -.-> ModelingApproaches

        %% ARTIFACTS B
        subgraph ArtifactsB [PHASE B OUTPUT ARTIFACTS]
            direction LR
            OutB1[(Fact Tables<br/>Definition)]
            OutB2[(Conformed<br/>Dimensions)]
            OutB3[(Hubs / Links<br/>/ Satellites)]
            OutB4[(KPI & Metric<br/>Catalog)]
            OutB5[(Logical<br/>Data Model)]
        end
        class ArtifactsB artifactBox
        B10 -.-> ArtifactsB
    end

    %% =======================
    %% PHASE C: IMPLEMENTATION
    %% =======================
    subgraph PhaseC_Wrap [ ]
        direction TB
        TitleC[PHASE C - TECHNOLOGY (IMPLEMENTATION)<br/>Build, Govern & Operate the Data Platform]:::phaseC
        
        C11[11. Source-to-Target Mapping Agent]:::agentC
        C12[12. Platform Design Agent]:::agentC
        C13[13. Ingestion Design Agent]:::agentC
        C14[14. Transformation Agent]:::agentC
        C15[15. Data Quality Agent]:::agentC
        C16[16. Semantic Layer Agent]:::agentC
        C17[17. Governance & Lineage Agent]:::agentC
        C18[18. Orchestration & Observability Agent]:::agentC

        C11 --> C12
        C11 --> C14
        C12 --> C13
        C13 --> C14
        C14 --> C15
        C15 --> C16
        C16 --> C17
        C17 --> C18

        %% ARTIFACTS C
        subgraph ArtifactsC [PHASE C OUTPUT ARTIFACTS]
            direction LR
            OutC1[(Physical<br/>Data Model)]
            OutC2[(Data Quality<br/>Reports)]
            OutC3[(Semantic Models<br/>& Metrics)]
            OutC4[(Lineage<br/>Graph)]
            OutC5[(Operational<br/>Runbooks)]
        end
        class ArtifactsC artifactBox
        C18 -.-> ArtifactsC
    end

    %% =======================
    %% RIGHT COLUMN: Consumers
    %% =======================
    subgraph Consumers [CONSUMERS & OUTCOMES]
        direction TB
        Con1[Analytics / BI]
        Con2[Self-Service Analytics]
        Con3[AI / LLM Agents]
        Con4[Operational Applications]
        Con5[Data Sharing]
        Con6[Compliance & Audit]
    end

    %% =======================
    %% BOTTOM: AWS Platform
    %% =======================
    subgraph AWS [ENTERPRISE DATA PLATFORM & FOUNDATION SERVICES]
        direction LR
        subgraph StorageCompute [Storage & Compute]
            S3[Amazon S3 / Redshift / Athena]
        end
        subgraph CatalogMeta [Catalog & Metadata]
            Glue[AWS Glue / Lake Formation / OpenSearch]
        end
        subgraph StreamingInt [Streaming & Integration]
            Kin[Amazon Kinesis / EventBridge / DMS]
        end
        subgraph Security [Security & Foundation]
            IAM[IAM / KMS / CloudWatch / Lambda / Step Functions]
        end
    end
    class AWS aws

    %% =======================
    %% HIGH-LEVEL PIPELINE FLOWS
    %% =======================
    UI --> PhaseA_Wrap
    DataSources --> PhaseA_Wrap
    PhaseA_Wrap ===> PhaseB_Wrap
    PhaseB_Wrap ===> PhaseC_Wrap
    PhaseC_Wrap --> Consumers
    ArtifactsC -.-> AWS
```
