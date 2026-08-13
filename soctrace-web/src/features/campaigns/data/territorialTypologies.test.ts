import { describe, expect, it } from "vitest";
import dossier from "./generated/mijas-2027-block-d-territorial-clusters.json";
import index from "./generated/block-c/territory-index.json";
import { mijas2027TypologyPresentation } from "./mijas-2027-typologies";

describe("Mijas territorial typologies projection", () => {
  it("reconciles membership, population, labels, and Block C identities", () => {
    const memberships=dossier.territoryMembership;
    expect(memberships).toHaveLength(37);
    expect(new Set(memberships.map(item=>item.seccion_id)).size).toBe(37);
    expect(dossier.clusterProfiles.reduce((sum,group)=>sum+group.population_represented,0)).toBe(92211);
    expect(dossier.clusterProfiles.reduce((sum,group)=>sum+group.section_count,0)).toBe(37);
    expect(new Set(index.map(item=>item.sectionId))).toEqual(new Set(memberships.map(item=>item.seccion_id)));
    expect(dossier.clusterProfiles.every(group=>group.cluster_id in mijas2027TypologyPresentation.groups)).toBe(true);
    expect(memberships.filter(item=>item.transitional).map(item=>item.seccion_id)).toEqual([
      "2907001003","2907001006","2907001012","2907001013","2907001021","2907001037",
    ]);
  });
});
