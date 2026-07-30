type Positionable = {
  position?: number | null;
};

export const sortByPosition = <Item extends Positionable>(
  items: Item[],
): Item[] =>
  items
    .map((item, index) => ({ item, index }))
    .sort((left, right) => {
      const leftPosition = left.item.position ?? Number.POSITIVE_INFINITY;
      const rightPosition = right.item.position ?? Number.POSITIVE_INFINITY;

      return leftPosition - rightPosition || left.index - right.index;
    })
    .map(({ item }) => item);
