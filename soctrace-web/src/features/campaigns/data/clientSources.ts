export const campaignClientSources = {
  population: "INE",
  electoral: "Ministerio del Interior",
  builtEnvironment: "Catastro",
  analysis: "Investigaciones propias de soctrace",
} as const;

export const campaignSourceLine = Object.values(campaignClientSources).join(" · ");
