type HighlightExcerptProps = {
  text: string;
  search: string;
};

export const HighlightExcerpt = ({ text, search }: HighlightExcerptProps) => {
  const index = text.toLowerCase().indexOf(search.toLowerCase());

  if (index === -1) {
    return <span>{text}</span>;
  }

  return (
    <span>
      {text.substring(0, index)}

      <span className="rounded-sm bg-warning">
        {text.substring(index, index + search.length)}
      </span>

      {text.substring(index + search.length)}
    </span>
  );
};
