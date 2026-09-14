from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Helvetica", "B", 16)
pdf.cell(0, 10, "AHMET YILMAZ", ln=True)
pdf.set_font("Helvetica", "", 11)
pdf.cell(0, 8, "FRONTEND DEVELOPER", ln=True)
pdf.cell(0, 6, "Istanbul, Turkey | ahmet.yilmaz.test@example.com | github.com/ahmetyilmaz-test", ln=True)
pdf.ln(4)

def section(title):
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, title, ln=True)
    pdf.set_font("Helvetica", "", 11)

section("PROFILE SUMMARY")
pdf.multi_cell(0, 6,
    "Frontend developer with 3+ years of experience building responsive, accessible, and "
    "performant web applications using React and modern JavaScript tooling. Passionate about "
    "component-driven architecture, design systems, and delivering smooth user experiences."
)
pdf.ln(2)

section("PROFESSIONAL EXPERIENCE")
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 6, "Frontend Developer - Pixelworks Digital Agency (2023 - Present)", ln=True)
pdf.set_font("Helvetica", "", 11)
pdf.multi_cell(0, 6,
    "- Built and maintained component libraries in React and TypeScript, used across 6+ client products.\n"
    "- Migrated a legacy jQuery codebase to a modern React + Vite stack, cutting page load time by 40%.\n"
    "- Implemented responsive layouts with Tailwind CSS and CSS Grid for cross-device consistency.\n"
    "- Collaborated closely with UX designers in Figma to translate mockups into pixel-perfect interfaces."
)
pdf.ln(2)
pdf.set_font("Helvetica", "B", 11)
pdf.cell(0, 6, "Junior Web Developer - Loomify Startup (2022 - 2023)", ln=True)
pdf.set_font("Helvetica", "", 11)
pdf.multi_cell(0, 6,
    "- Developed landing pages and marketing sites using HTML, CSS, and vanilla JavaScript.\n"
    "- Integrated REST APIs for a customer dashboard built with Vue.js.\n"
    "- Wrote unit tests with Jest and improved test coverage from 20% to 65%."
)
pdf.ln(2)

section("PROJECTS")
pdf.multi_cell(0, 6,
    "Personal Portfolio & Blog - Built with Next.js, MDX, and Tailwind CSS, deployed on Vercel.\n"
    "Recipe Sharing App - React Native mobile app with Firebase authentication and Firestore backend."
)
pdf.ln(2)

section("SKILLS")
pdf.multi_cell(0, 6,
    "Languages: JavaScript (ES6+), TypeScript, HTML5, CSS3\n"
    "Frameworks/Libraries: React, Next.js, Vue.js, Redux, Tailwind CSS, Styled Components\n"
    "Tools: Git, Webpack, Vite, Figma, Jest, Storybook\n"
    "Other: Responsive Design, Web Accessibility (WCAG), REST APIs, Basic UI/UX Design"
)
pdf.ln(2)

section("EDUCATION")
pdf.multi_cell(0, 6, "B.Sc. in Computer Engineering - Marmara University (2018 - 2022)")
pdf.ln(2)

section("LANGUAGES")
pdf.multi_cell(0, 6, "Turkish: Native | English: B2 (Upper-Intermediate)")

pdf.output("test_cv_frontend_developer.pdf")
print("PDF created: test_cv_frontend_developer.pdf")
