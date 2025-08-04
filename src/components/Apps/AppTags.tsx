import { isNumber } from '@utils';

import { Badge, Render } from '@components';

const TAGS_RESTRICTION_AMOUNT = 3;

type Props = {
  tags?: string[];
  restrictionAmount?: number | null;
};

export const AppTags = ({
  tags = [],
  restrictionAmount = TAGS_RESTRICTION_AMOUNT,
}: Props) => {
  const { visibleTags, otherTags } = (() => {
    if (isNumber(restrictionAmount)) {
      return {
        visibleTags: tags.slice(0, restrictionAmount),
        otherTags: tags.slice(restrictionAmount),
      };
    }

    return { visibleTags: tags, otherTags: [] };
  })();

  const makeTag = (tag: string) => (
    <Badge className="text-body-small" key={tag}>
      {tag}
    </Badge>
  );

  if (!tags.length) {
    return null;
  }

  return (
    <div className="flex shrink-0 gap-1">
      {visibleTags.map(makeTag)}
      <Render if={!!otherTags.length}>
        <Badge className="text-body-small">+{otherTags.length}</Badge>
      </Render>
    </div>
  );
};
