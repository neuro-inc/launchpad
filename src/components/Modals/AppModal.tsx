import { faLink } from '@fortawesome/pro-light-svg-icons';

import { App } from '@typings';

import { AppItemLink } from '@components/Apps/AppItemLink';
import { Button, Image, Render } from '@components/Shared';
import { Logo } from '@components/Ui/Logo';

type Props = {
  app: App;
};

export const AppModal: React.FC<Props> = ({
  app: {
    logo,
    title,
    shortDescription,
    description,
    documentationUrls,
    externalUrls,
  },
}) => {
  const makeDocumentationLink = ({
    text,
    url,
  }: App['documentationUrls'][number]) => (
    <AppItemLink external key={url} to={url} title={text} />
  );

  const makeReferenceLink = ({ text, url }: App['externalUrls'][number]) => (
    <AppItemLink icon={faLink} key={url} to={url} title={text} />
  );

  return (
    <div className="relative flex w-[800px] max-w-full flex-col gap-8 overflow-auto rounded-2xl bg-white p-14">
      <div className="relative flex min-w-0 gap-9">
        <div className="flex size-[160px] shrink-0 items-center justify-center overflow-hidden rounded-lg border border-neural-02 bg-white">
          <Render if={logo}>
            <Image src={logo} alt="Logo" />
          </Render>
          <Render if={!logo}>
            <Logo.Icon className="size-28" />
          </Render>
        </div>

        <div className="flex basis-full flex-col gap-3">
          <p className="text-h4">{title}</p>
          <Render if={shortDescription}>
            <p className="text-neural-04">{shortDescription}</p>
          </Render>
          <div className="mt-auto flex justify-end">
            <Button className="px-10">Open</Button>
          </div>
        </div>
      </div>
      <Render if={description}>
        <p className="text-neural-04">{description}</p>
      </Render>
      <Render if={documentationUrls}>
        <div className="flex flex-col gap-3">
          <p className="text-h6">Documentation</p>
          {documentationUrls.map(makeDocumentationLink)}
        </div>
      </Render>
      <Render if={externalUrls}>
        <div className="flex flex-col gap-3">
          <p className="text-h6">References</p>
          {externalUrls.map(makeReferenceLink)}
        </div>
      </Render>
    </div>
  );
};
