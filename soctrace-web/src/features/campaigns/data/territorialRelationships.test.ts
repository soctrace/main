import { describe,expect,it } from "vitest";
import full from "./generated/mijas-2027-block-e-cross-variable-analysis.json";
import client from "./generated/mijas-2027-block-e-client.json";
import index from "./generated/block-c/territory-index.json";
import { mijas2027TypologyPresentation } from "./mijas-2027-typologies";

describe("Block E client projection",()=>{
 it("traces selected evidence and keeps the projection bounded",()=>{
  const source=new Map(full.bivariateRelationships.map(x=>[x.relationship_id,x]));
  for(const item of client.selectedRelationships) expect(item).toEqual(source.get(item.relationship_id));
  expect(client.selectedRelationships.length).toBeLessThan(30);
  expect(client.reducedRelationshipNetwork).toHaveLength(18);
  expect(client.reducedRelationshipNetwork.every(x=>x.network==="client-ready reduced")).toBe(true);
  expect(client.sectionPoints).toHaveLength(37);
  expect(new Set(client.sectionPoints.map(x=>x.sectionId))).toEqual(new Set(index.map(x=>x.sectionId)));
  expect(client.residualTerritories.every(x=>index.some(i=>i.sectionId===x.section_id))).toBe(true);
  expect(new Set(client.typologyComparisons.map(x=>x.group))).toEqual(new Set(Object.keys(mijas2027TypologyPresentation.groups)));
 });
});
