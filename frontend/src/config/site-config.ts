export const siteConfig = {
  title: "ScholarFlow Journal",
  description: "A leading open-access journal for interdisciplinary research and academic excellence.",
  issn: "2073-4433",
  impact_factor: "3.2",
  links: {
    home: "/",
    about: "/about",
    contact: "/about",
    submit: "/submit",
    dashboard: "/dashboard",
    journals: "/journals",
    topics: "/topics",
    resources: {
      authorGuidelines: "/submit",
      editorialPolicies: "/about",
      openAccessPolicy: "/about",
    },
  },
  copyright: `Copyright © ${new_stringDate().getFullYear()} ScholarFlow`,
};

function new_stringDate() {
  return new Date();
}
