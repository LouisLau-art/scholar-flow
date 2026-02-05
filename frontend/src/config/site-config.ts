export const siteConfig = {
  title: "ScholarFlow Journal",
  description: "A leading open-access journal for interdisciplinary research and academic excellence.",
  issn: "2073-4433",
  impact_factor: "3.2",
  links: {
    about: "/about",
    contact: "/contact",
    submit: "/submit",
    dashboard: "/dashboard",
  },
  copyright: `Copyright © ${new_stringDate().getFullYear()} ScholarFlow`,
};

function new_stringDate() {
  return new Date();
}
