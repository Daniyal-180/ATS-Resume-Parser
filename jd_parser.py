import re
import fitz
import docx
# ==============================
# Expanded Master Skills Database (Updated with your stack)
# ==============================

SKILLS_DB = [
    # Programming & Core Languages
    "Python", "Java", "JavaScript", "TypeScript", "C", "C++", "C#", ".NET", ".NET Core",
    "PHP", "Laravel", "Ruby", "Ruby on Rails", "Go", "Golang", "Swift", "SwiftUI", "Kotlin", "R",
    "Rust", "Scala", "Perl", "Lua", "Elixir", "Haskell", "Dart",

    # Web & Frontend
    "HTML", "HTML5", "CSS", "CSS3", "SASS", "SCSS", "LESS", "Bootstrap", "Tailwind CSS", "Material UI",
    "React.js", "React Native", "Angular", "Vue.js", "jQuery",
    "Next.js", "Nuxt.js", "Gatsby", "Ember.js", "Backbone.js",
    "Ajax", "JSON", "GSAP Animation",

    # Databases & Data Storage
    "SQL", "MySQL", "PostgreSQL", "MongoDB", "Firebase", "NoSQL",
    "Oracle", "SQLite", "SQL Server", "Cassandra", "DynamoDB",
    "Redis", "Memcached", "Elasticsearch", "CouchDB", "Neo4j",
    "GraphQL", "Amazon Aurora",

    # Backend / API Development
    "API Development", "API Integrations", "REST", "REST API", "SOAP", "gRPC", "RESTful APIs",
    "WebSocket", "Socket.io", "GraphQL API", "Node.js", "Express.js", "Nest.js",

    # Cloud & DevOps / Infrastructure
    "AWS", "Azure", "GCP", "Google Cloud", "DevOps",
    "EC2", "S3", "Lambda", "CloudFormation",
    "Docker", "Kubernetes", "K8s", "Terraform", "Ansible", "Chef", "Puppet",
    "Jenkins", "Travis CI", "CircleCI", "GitHub Actions", "CI/CD", "Git", "GitHub", "GitLab", "Bitbucket",
    "Linux", "Ubuntu", "CentOS", "Bash", "Shell Scripting", "PowerShell",
    "Windows Server", "Nginx", "Apache", "HAProxy", "Load Balancing",
    "Message Queues", "RabbitMQ", "Kafka", "ActiveMQ", "SQS", "SNS",

    # Data, Analytics, AI / ML / Big Data
    "Excel", "Power BI", "Tableau", "Looker", "Metabase",
    "Apache Spark", "Hadoop", "Hive", "Pig", "Flink",
    "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "Keras", "PyTorch", "OpenCV",
    "XGBoost", "LightGBM", "CatBoost", "Matplotlib", "Seaborn", "Plotly",
    "Statsmodels", "NLTK", "spaCy", "Computer Vision", "Deep Learning", "DL", "cv2",
    "Natural Language Processing", "NLP", "Recommender Systems", "Time Series", "Graph ML",
    "ML", "Machine Learning", "Data Science", "Statistics",
    "AI Automation", "Automations",

    # Mapping & Visualization
    "Mapbox", "CesiumJS", "GIS", "Geospatial Analysis",

    # Design & Collaboration Tools
    "Canva", "Figma", "Adobe XD", "Sketch", "Photoshop", "Illustrator",

    # CMS & Website Builders
    "WordPress", "WooCommerce", "Elementor",

    # Architecture / Patterns / Design
    "Microservices", "Monolithic Architecture", "Serverless", "Event-Driven Architecture",
    "MVC", "MVVM", "Domain-Driven Design", "CQRS", "Event Sourcing",
    "API Gateway", "Service Mesh", "Scaling", "Caching", "Sharding", "Replication",
    "ElasticSearch", "CDN",

    # Testing & QA
    "Selenium", "JUnit", "JUnit5", "JUnit4", "TestNG", "PyTest", "Mocha", "Jasmine",
    "Cypress", "Playwright", "Karma", "Protractor", "Postman", "REST Assured",
    "API Testing", "Load Testing", "Performance Testing", "JMeter", "Gatling", "API Integration",
    "Mockito", "Selenium WebDriver", "Cucumber", "Robot Framework",

    # Security / Authentication / Compliance
    "OAuth", "JWT", "OpenID", "SAML", "LDAP", "SSL/TLS", "HTTPS",
    "Encryption", "PKI", "Penetration Testing", "Vulnerability Assessment",
    "Network Security", "Firewalls", "IDS", "IPS", "WAF", "SIEM", "Splunk",
    "OWASP", "Security Auditing", "GDPR", "SOC2", "PCI-DSS", "ISO 27001",

    # Dev / Tooling / Monitoring
    "Docker Compose", "Helm", "Istio", "Linkerd", "Prometheus", "Grafana",
    "Logstash", "Kibana", "ELK Stack", "Fluentd", "Splunk", "Datadog",
    "Jira", "Confluence", "Trello", "Slack", "Microsoft Teams",

    # Mobile & Game Development
    "Android", "iOS", "Flutter", "Ionic", "Unity", "Unreal Engine", "Game Development",

    # Blockchain / Web3
    "Blockchain", "Ethereum", "Solidity", "Smart Contracts",

    # Soft Skills
    "Communication", "Problem Solving", "Problem-Solving", "Teamwork", "Leadership",
    "Adaptability", "Time Management", "Analytical Thinking", "Analytical",
    "Critical Thinking", "Creativity", "Decision Making",
    "Interpersonal Skills", "Planning", "Mentoring", "Collaboration",
    "Problem Solver", "Learning Aptitude", "Team Player",
    "Presentation Skills", "Conflict Resolution", "Attention to Detail",
    "Negotiation", "Empathy", "Customer Focus", "Agile Methodologies",
    "Scrum", "Kanban", "Lean", "Project Management", "Stakeholder Management"
]


# ==============================
# Education Keywords for JD Parsing
# ==============================

education = [
    # Doctorate
    "PHD", "DOCTORATE", "D.PHIL",

    # Master's level
    "MASTER", "MASTERS", "MS", "M.SC", "MSC", "M.TECH", "MTECH",
    "MBA", "M.COM", "MCA", "M.ED", "M.PHIL",

    # Bachelor's level
    "BACHELOR", "BACHELORS", "BS", "BSC", "B.SC", "BA", "B.A",
    "BBA", "B.COM", "BCA", "B.TECH", "BTECH", "BE", "B.E", "BSCS",
    "BSIT", "BSSE", "BCE", "BS SOFTWARE ENGINEERING",
    "BS INFORMATION TECHNOLOGY", "BS COMPUTER SCIENCE",

    # Diploma / Intermediate
    "INTERMEDIATE", "HSC", "SSC", "DIPLOMA", "ASSOCIATE DEGREE",
    "MATRIC", "HIGH SCHOOL", "SECONDARY SCHOOL",
    "O-LEVEL", "A-LEVEL", "GED"
]


experience_reg = [
        r"(\d+)\+?\s*(?:year|years)",  # 2 years, 3+ years
        r"(\d+)\s*-\s*(\d+)\s*(?:year|years)",  # 2-3 years, 5-7 years
        r"\b(?:minimum|at least)\s+\d+\s*(?:year|years)\b",  # minimum 3 years
        r"Minimum\s+(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*years?",
        r"\b(?:preferred)\s+\d+\s*(?:year|years)\b",  # preferred 5 years
        r"\b(?:fresher|fresh graduate|entry level)\b"  # fresher / entry level
]

def parse_job_description(text: str):

    # --- Extract Skills ---
    found_skills = [
        skill for skill in SKILLS_DB
        if re.search(rf"\b{re.escape(skill)}\b", text, re.IGNORECASE)
    ]
    skills_str = ", ".join(found_skills)

    # --- Extract Experience ---

    min_exp_list = []

    for p in experience_reg:
        matches = re.findall(p, text, re.I)
        for match in matches:
            if isinstance(match, tuple):
                try:
                    min_exp_list.append(float(match[0]))
                except ValueError:
                    continue
            else:
                if re.search(r"\b(fresher|fresh graduate|entry level)\b", match, re.I):
                    min_exp_list.append(0)
                else:
                    try:
                        min_exp_list.append(int(match))
                    except ValueError:
                        continue

    min_experience = min(min_exp_list) if min_exp_list else 0


    # --- Extract Education ---
    found_education = []
    for edu in education:
        if re.search(rf"\b{re.escape(edu)}\b", text, re.I):
            found_education.append(edu)

    found_education = list(set(found_education))

    return {
        "skills": skills_str,
        "min_experience": min_experience,
        "education": found_education,
    }


# ==============================
# File Readers
# ==============================
def read_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text("text")
    return text


def read_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])


# ==============================
# Main
# ==============================
if __name__ == "__main__":
    # file_path = r"c:\Users\user\Downloads\jd2.pdf"
    #
    # if file_path.lower().endswith(".pdf"):
    #     jd_text = read_pdf(file_path)
    # elif file_path.lower().endswith(".docx"):
    #     jd_text = read_docx(file_path)
    # else:
    #     raise ValueError("Unsupported file format. Only PDF and DOCX are allowed.")
    jd_text = """About the Role: We are offering an exciting opportunity for a fresher to join our team as a Data Analyst Intern. This is a paid internship program that will provide you with valuable hands-on experience, mentorship from senior team members, and the potential to transition into a permanent full-time role based on performance.

As a Data Analyst Intern, you will be involved in supporting data-driven decision-making by gathering, analysing, and presenting insights through various tools and platforms. If you have a passion for data, problem-solving, and driving business outcomes, we encourage you to apply.

Key Responsibilities:

Assist in maintaining and developing Power BI dashboards
Perform day-to-day ad-hoc requests and client reporting
Perform analysis on key performance indicators (KPIs)
Work closely with Senior Analysts to gain exposure to data processing, reporting, and analytics
Provide data-driven insights to support business decisions
Clean and organize data from various sources, ensuring accuracy and attention to detail
Support the team in creating visually appealing and informative reports and presentations
Learn to automate reports using Excel, SQL, and Power BI

Requirements

Qualifications & Requirements:

Strong Skills in:
Microsoft Excel (pivot tables, VLOOKUP / XLOOKUP, data visualization, etc.)
Power BI (basic dashboard development and maintenance)
SQL (basic querying skills)
Basic knowledge of maintaining and developing Power BI dashboards
Demonstrated attention to detail and problem-solving skills
Strong communication skills, both verbal and written
Ability to handle and analyse data, identify trends, and provide insights
Fresh graduates or individuals new to the field are encouraged to apply
 Preferred: Certifications in Excel, Power BI, or SQL will be an added advantage

What We Offer:

A structured internship with the opportunity to transition into a full-time Data Analyst role
Hands-on training and mentorship from Senior Business Intelligence Analyst
Exposure to real-world business data and analytics projects
A dynamic and collaborative work environment
The chance to work on meaningful projects that impact key business decisions

Why Join Us:

Opportunity to learn and grow in a fast-paced environment
Gain practical experience working with industry-standard tools and techniques
Build a solid foundation in data analytics and business intelligence"""
    result = parse_job_description(jd_text)
    print(result)
