import { faLink } from '@fortawesome/pro-light-svg-icons';

import { App } from '@typings';
import { path } from '@utils/path';

import { AppItemLink } from '@components/Apps/AppItemLink';
import { Image, Link, Render } from '@components/Shared';
import { Logo } from '@components/Ui/Logo';

type Props = {
  app: App;
};

export const AppModal: React.FC<Props> = ({
  app: {
    logo,
    title,
    descriptionShort,
    descriptionLong,
    documentationUrls,
    externalUrls,
    launchpadAppName,
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
    <div className="relative flex w-[800px] max-w-full flex-col gap-8 overflow-auto rounded-2xl bg-white p-14 sm:px-4 md:px-8">
      <div className="relative flex min-w-0 gap-9 sm:gap-5">
        <div className="flex size-[160px] shrink-0 items-center justify-center overflow-hidden rounded-lg border border-neural-02 bg-white sm:size-20">
          <Render if={logo}>
            <Image transition src={logo} width={160} height={160} alt="Logo" />
          </Render>
          <Render if={!logo}>
            <Logo.Icon className="size-28" />
          </Render>
        </div>

        <div className="flex basis-full flex-col gap-3">
          <p className="text-h4">{title}</p>
          <Render if={descriptionShort}>
            <p className="text-neural-04 sm:-mt-2">{descriptionShort}</p>
          </Render>
          <div className="mt-auto flex justify-end">
            <Link
              blank
              external
              className="px-10 sm:w-full"
              href={path.app(launchpadAppName)}
            >
              Open
            </Link>
          </div>
        </div>
      </div>
      <Render if={descriptionLong}>
        <p className="text-neural-04">{descriptionLong}</p>
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
