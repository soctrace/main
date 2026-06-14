export type ElectoralPartyInput = {
  party: string;
  votes?: number;
  percentage?: number;
};

export type DHondtSeatResult = {
  party: string;
  seats: number;
  votes: number;
  percentage: number;
  votesPerSeat: number | null;
};

export function calculateDHondtSeats({
  parties,
  totalSeats,
  thresholdPct,
}: {
  parties: ElectoralPartyInput[];
  totalSeats: number;
  thresholdPct: number;
}): DHondtSeatResult[] {
  const normalized = parties
    .map((item) => ({
      party: item.party,
      votes: item.votes ?? item.percentage ?? 0,
      percentage: item.percentage ?? 0,
    }))
    .filter((item) => item.party && item.votes > 0 && item.percentage >= thresholdPct);

  const quotients = normalized.flatMap((item) =>
    Array.from({ length: totalSeats }, (_, index) => ({
      ...item,
      quotient: item.votes / (index + 1),
    })),
  );

  const seatCounts = new Map<string, DHondtSeatResult>();
  quotients
    .sort((a, b) => b.quotient - a.quotient || b.votes - a.votes || a.party.localeCompare(b.party))
    .slice(0, totalSeats)
    .forEach((item) => {
      const current = seatCounts.get(item.party) ?? {
        party: item.party,
        seats: 0,
        votes: item.votes,
        percentage: item.percentage,
        votesPerSeat: null,
      };
      const seats = current.seats + 1;
      seatCounts.set(item.party, {
        ...current,
        seats,
        votesPerSeat: current.votes / seats,
      });
    });

  return Array.from(seatCounts.values())
    .filter((item) => item.seats > 0)
    .sort((a, b) => b.seats - a.seats || b.votes - a.votes || a.party.localeCompare(b.party));
}
