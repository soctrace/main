import validatedCatalog from "./validated_test_catalog.json";

export type AskSocTraceTest = {
  id: string;
  category: string;
  title: string;
  prompt: string;
  status: "available" | "coming_soon";
  tool?: string;
  validationStatus?: "passed" | "failed";
  expectedChartType?: "bar" | "line" | "scatter" | "map" | "table" | "none";
  description?: string;
};

type ValidatedCatalogRow = {
  id: string;
  question: string;
  status: "available" | "coming_soon";
  selected_tool?: string | null;
  required_tool?: string | null;
  validation_status?: "passed" | "failed";
};

const testsByCategory: Array<[string, Array<[string, string?]>]> = [
  ["Demografia - Poblacion", [
    ["¿Cuál es la sección con mayor población?", "bar"],
    ["¿Cuál es la sección con menor población?", "bar"],
    ["¿Qué secciones superan los 5.000 habitantes?", "bar"],
    ["¿Cuál es la población total de Mijas?", "none"],
    ["¿Cómo ha evolucionado la población desde 2021?", "line"],
    ["¿Qué zonas han crecido más?", "bar"],
  ]],
  ["Demografia - Edad", [
    ["¿Cuál es la sección más joven?", "bar"],
    ["¿Cuál es la más envejecida?", "bar"],
    ["¿Dónde viven más menores de 18 años?", "bar"],
    ["¿Dónde viven más personas mayores de 65 años?", "bar"],
    ["¿Qué porcentaje de la población tiene menos de 30 años?", "bar"],
    ["¿Qué secciones tienen más población en edad laboral?", "bar"],
    ["¿Siempre ha sido la sección más joven?", "line"],
    ["¿Qué sección ha rejuvenecido más desde 2021?", "line"],
    ["¿Qué sección ha envejecido más desde 2021?", "line"],
    ["¿Qué sección ha envejecido más?", "line"],
    ["¿Qué secciones tienen más menores de 30 años?", "bar"],
    ["¿Qué secciones tienen más mayores de 65 años?", "bar"],
    ["¿Qué porcentaje de población joven tiene cada sección?", "bar"],
    ["¿Qué porcentaje de población jubilada tiene cada sección?", "bar"],
    ["¿Qué zonas tienen mayor dependencia demográfica?", "bar"],
  ]],
  ["Demografia - Cohortes", [
    ["¿Cuántas personas aproximadamente tendrán 18 años en 2027?", "bar"],
    ["¿Cuántas personas tendrán 18 años en 2027?", "bar"],
    ["¿Qué secciones tendrán más nuevos votantes en 2027?", "bar"],
    ["¿Qué zonas concentran más jóvenes que podrán votar por primera vez en 2027?", "bar"],
    ["¿Cuántas personas tenían entre 18 y 22 años en 2023?", "table"],
    ["¿Cuántas personas entre 18 y 35 años viven en Riviera Sur?", "none"],
    ["¿Qué secciones concentran más jóvenes?", "bar"],
    ["¿Qué secciones concentran más población joven?", "bar"],
    ["¿Qué secciones concentran más jubilados?", "bar"],
    ["¿Cuántas personas mayores de 65 años viven en Mijas?", "none"],
  ]],
  ["Electoral - Partido dominante", [
    ["¿Dónde gana el PP siempre?", "table"],
    ["¿Dónde gana siempre el PP?", "table"],
    ["¿Dónde gana el PSOE siempre?", "table"],
    ["¿Dónde gana siempre el PSOE?", "table"],
    ["¿Dónde gana VOX siempre?", "table"],
    ["¿Dónde gana siempre VOX?", "table"],
    ["¿Cuál es el partido históricamente dominante en cada sección?", "table"],
    ["¿Qué partido domina históricamente en Riviera Sur?", "bar"],
    ["¿Qué partido es históricamente más fuerte en la sección más joven?", "bar"],
    ["¿Qué partido domina la sección más joven?", "bar"],
    ["¿Qué partido domina la sección más envejecida?", "bar"],
    ["¿Cuál es la sección más favorable al PP?", "bar"],
    ["¿Cuál es la más favorable al PSOE?", "bar"],
    ["¿Cuál es la más favorable a VOX?", "bar"],
    ["¿Cuál es la media histórica de voto del PP?", "bar"],
    ["¿Cuál es la media histórica de voto del PSOE?", "bar"],
  ]],
  ["Electoral - Participacion", [
    ["¿Qué sección tiene más abstención?", "bar"],
    ["¿Cuál tiene menos abstención?", "bar"],
    ["¿Dónde vota más la gente?", "bar"],
    ["¿Dónde vota menos la gente?", "bar"],
    ["¿Qué zonas han reducido más la participación?", "line"],
  ]],
  ["Electoral - Evolucion", [
    ["¿Qué secciones cambiaron más entre 2019 y 2023?", "line"],
    ["¿Dónde perdió más apoyo el PSOE?", "line"],
    ["¿Dónde ganó más apoyo el PP?", "line"],
    ["¿Dónde creció más VOX?", "line"],
    ["¿Dónde aparecen más partidos locales?", "bar"],
  ]],
  ["Electoral - Competitividad", [
    ["¿Cuáles son las secciones más disputadas?", "bar"],
    ["¿Dónde hay empate técnico entre PP y PSOE?", "bar"],
    ["¿Dónde tiene más margen de victoria el partido ganador?", "bar"],
    ["¿En qué sección gana con más diferencia el PSOE?", "bar"],
    ["¿En qué sección gana con más diferencia el PP?", "bar"],
    ["¿Cuáles son las secciones más competitivas?", "bar"],
    ["¿Qué secciones son más volátiles electoralmente?", "bar"],
    ["¿Qué secciones son más conservadoras?", "bar"],
    ["¿Qué secciones son más progresistas?", "bar"],
  ]],
  ["Consultoria politica - Movilizacion", [
    ["¿Dónde debería concentrar esfuerzos el PSOE?", "bar"],
    ["¿Dónde debería concentrar esfuerzos el PP?", "bar"],
    ["¿Qué secciones tienen más abstencionistas potenciales?", "bar"],
    ["¿Dónde hay más jóvenes que no votaron?", "bar"],
    ["¿Qué secciones combinan alta abstención y mucho voto de izquierdas?", "scatter"],
    ["¿Qué secciones combinan alta abstención y mucho voto de derechas?", "scatter"],
  ]],
  ["Consultoria politica - Segmentacion", [
    ["¿Dónde vive el votante medio del PP?", "table"],
    ["¿Dónde vive el votante medio del PSOE?", "table"],
    ["¿Qué características tienen las secciones donde gana VOX?", "table"],
    ["¿Qué secciones son más sensibles a una campaña de movilización?", "bar"],
  ]],
  ["Consultoria politica - Oportunidades", [
    ["¿Cuáles son las mejores secciones para ganar un concejal adicional?", "bar"],
    ["¿Dónde sería más eficiente invertir 10.000 € en campaña?", "bar"],
    ["¿Qué secciones presentan más indecisión estructural?", "bar"],
  ]],
  ["Sociologia - Estructura social", [
    ["¿Qué secciones tienen más jóvenes y menos renta?", "scatter"],
    ["¿Qué secciones tienen más mayores y más renta?", "scatter"],
    ["¿Dónde existe mayor polarización demográfica?", "bar"],
    ["¿Qué zonas son más homogéneas?", "bar"],
  ]],
  ["Sociologia - Vulnerabilidad", [
    ["¿Qué secciones presentan más vulnerabilidad social?", "bar"],
    ["¿Qué zonas combinan envejecimiento y baja renta?", "scatter"],
    ["¿Dónde hay más riesgo de exclusión social?", "bar"],
    ["¿Qué secciones requieren más servicios públicos?", "bar"],
  ]],
  ["Sociologia - Cohesion", [
    ["¿Qué zonas parecen más cohesionadas socialmente?", "bar"],
    ["¿Qué zonas muestran perfiles más diversos?", "bar"],
  ]],
  ["Ciencia politica - Estabilidad electoral", [
    ["¿Qué secciones son más estables?", "bar"],
    ["¿Qué secciones son más volátiles?", "bar"],
    ["¿Qué secciones cambian de partido ganador según la elección?", "table"],
    ["¿Dónde existen patrones electorales persistentes?", "table"],
  ]],
  ["Ciencia politica - Comportamiento politico", [
    ["¿La juventud vota más a la izquierda?", "scatter"],
    ["¿La renta alta favorece al PP?", "scatter"],
    ["¿Existe relación entre abstención y renta?", "scatter"],
    ["¿Existe relación entre edad y participación?", "scatter"],
  ]],
  ["Economia - Renta", [
    ["¿Cuál es la sección más rica?", "bar"],
    ["¿Cuál es la más pobre?", "bar"],
    ["¿Qué secciones tienen mayor renta media?", "bar"],
    ["¿Qué secciones tienen menor renta media?", "bar"],
    ["¿Qué secciones tienen mayor renta?", "bar"],
    ["¿Qué secciones tienen menor renta?", "bar"],
    ["¿Qué zonas combinan renta alta y población joven?", "scatter"],
    ["¿Qué zonas combinan renta baja y envejecimiento?", "scatter"],
    ["¿Qué zonas combinan renta baja y abstención elevada?", "scatter"],
  ]],
  ["Economia - Desigualdad", [
    ["¿Qué zonas muestran mayor desigualdad?", "bar"],
    ["¿Dónde existe más diferencia entre renta individual y renta del hogar?", "bar"],
  ]],
  ["Economia - Desarrollo", [
    ["¿Qué zonas tienen mejor perfil económico?", "bar"],
    ["¿Qué zonas muestran señales de vulnerabilidad económica?", "bar"],
  ]],
  ["Inmobiliario - Mercado", [
    ["¿Qué secciones tienen mayor valor inmobiliario?", "bar"],
    ["¿Qué zonas tienen mayor valor inmobiliario?", "bar"],
    ["¿Qué secciones tienen menor valor inmobiliario?", "bar"],
    ["¿Dónde está el mercado más tensionado?", "bar"],
    ["¿Dónde están las oportunidades inmobiliarias?", "bar"],
    ["¿Qué zonas muestran mejor oportunidad inmobiliaria?", "bar"],
    ["¿Qué secciones tienen mayor presión residencial?", "bar"],
    ["¿Qué secciones son consideradas zona prime?", "bar"],
  ]],
  ["Inmobiliario - Construccion", [
    ["¿Qué zonas tienen mayor intensidad edificatoria?", "bar"],
    ["¿Qué zonas tienen más presión urbanística?", "bar"],
    ["¿Dónde se concentra más superficie construida?", "bar"],
  ]],
  ["Inmobiliario - Inversion", [
    ["¿Qué zonas combinan renta alta y valor inmobiliario alto?", "scatter"],
    ["¿Qué zonas parecen infravaloradas?", "bar"],
    ["¿Qué zonas tienen mayor potencial de revalorización?", "bar"],
  ]],
  ["Estadistica - Rankings", [
    ["Ordena las secciones por población.", "bar"],
    ["Ordena las secciones por renta.", "bar"],
    ["Ordena las secciones por edad media.", "bar"],
    ["Ordena las secciones por abstención.", "bar"],
  ]],
  ["Estadistica - Desviaciones", [
    ["¿Qué secciones están por encima de la media?", "bar"],
    ["¿Qué secciones son outliers?", "scatter"],
    ["¿Qué variable presenta más dispersión?", "bar"],
  ]],
  ["Estadistica - Distribuciones", [
    ["¿Cómo se distribuye la renta?", "bar"],
    ["¿Cómo se distribuye la edad?", "bar"],
    ["¿Cómo se distribuye la abstención?", "bar"],
  ]],
  ["Data Science - Correlaciones", [
    ["¿Qué variables se relacionan más con la abstención?", "scatter"],
    ["¿Qué variables se relacionan más con el voto al PP?", "scatter"],
    ["¿Qué variables se relacionan más con el voto al PSOE?", "scatter"],
  ]],
  ["Data Science - Clustering", [
    ["Agrupa secciones similares.", "scatter"],
    ["¿Qué secciones se parecen a Riviera Sur?", "table"],
    ["¿Qué secciones tienen perfiles equivalentes?", "table"],
  ]],
  ["Data Science - Scores", [
    ["Crea un índice de vulnerabilidad.", "bar"],
    ["Crea un índice de oportunidad electoral.", "bar"],
    ["Crea un índice de presión inmobiliaria.", "bar"],
    ["¿Qué zonas concentran más población y crecimiento?", "bar"],
    ["¿Qué zonas combinan juventud y crecimiento?", "bar"],
    ["¿Qué secciones presentan mejores indicadores territoriales?", "bar"],
  ]],
  ["Data Science - Prediccion", [
    ["¿Qué secciones podrían aumentar la abstención?", "bar"],
    ["¿Qué secciones podrían cambiar de ganador?", "bar"],
    ["¿Qué secciones podrían crecer más demográficamente?", "line"],
  ]],
  ["Conversacional - Contexto 1", [
    ["¿Cuál es la sección más joven?", "bar"],
    ["¿Siempre ha sido la más joven?", "line"],
    ["¿Qué partido es históricamente más fuerte allí?", "bar"],
    ["¿Y qué renta tiene?", "none"],
    ["¿Está por encima o por debajo de la media de Mijas?", "none"],
  ]],
  ["Conversacional - Contexto 2", [
    ["¿Dónde gana siempre el PP?", "table"],
    ["¿Cuál de esas secciones tiene más población?", "bar"],
    ["¿Y cuál es la más joven?", "bar"],
    ["¿Qué partido queda segundo en ella?", "bar"],
  ]],
];

function slugify(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function toolForPrompt(prompt: string) {
  return validatedByQuestion.get(prompt)?.selected_tool || validatedByQuestion.get(prompt)?.required_tool || undefined;
}

function statusForPrompt(prompt: string): AskSocTraceTest["status"] {
  return validatedByQuestion.get(prompt)?.status === "available" ? "available" : "coming_soon";
}

const validatedByQuestion = new Map(
  (validatedCatalog as ValidatedCatalogRow[]).map((item) => [item.question, item]),
);

export const askSocTraceTests: AskSocTraceTest[] = testsByCategory.flatMap(([category, prompts]) =>
  prompts.map(([prompt, expectedChartType], index) => ({
    id: `${slugify(category)}-${index + 1}`,
    category,
    title: prompt.replace(/[.。]$/, ""),
    prompt,
    status: statusForPrompt(prompt),
    tool: toolForPrompt(prompt),
    validationStatus: validatedByQuestion.get(prompt)?.validation_status,
    expectedChartType: expectedChartType as AskSocTraceTest["expectedChartType"],
  })),
);

export const askSocTraceTestCategories = Array.from(new Set(askSocTraceTests.map((test) => test.category)));
