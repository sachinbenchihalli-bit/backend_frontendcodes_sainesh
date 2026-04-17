import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import { defaultSchema } from 'rehype-sanitize';
import './MarkdownMessage.scss';

const MarkdownMessage: React.FC<{ text: string; onImageClick: (url: string, alt: string, title: string) => void }> = ({ text, onImageClick }) => {
  const createRenderer = (className: string, Element: keyof JSX.IntrinsicElements = 'span') => {
    return ({ node, children, ...props }: any) => {
      return <Element className={className} {...props}>{children}</Element>;
    };
  };

  const renderers = {
    h1: createRenderer("markdown-heading-h1", 'h1'),
    h2: createRenderer("markdown-heading-h2", 'h2'),
    h3: createRenderer("markdown-heading-h3", 'h3'),
    p: createRenderer("markdown-paragraph", 'p'),
    br: () => <br className="markdown-line-break" />,
    strong: createRenderer("markdown-bold", 'strong'),
    em: createRenderer("markdown-italic", 'em'),
    ul: createRenderer("markdown-list", 'ul'),
    ol: createRenderer("markdown-list", 'ol'),
    li: createRenderer("markdown-list-item", 'li'),
    table: ({ node, children, ...props }: any) => (
      <div className="overflow-x-auto">
        <table className="markdown-table" {...props}>{children}</table>
      </div>
    ),
    thead: createRenderer("markdown-table-head", 'thead'),
    tbody: createRenderer("markdown-table-body", 'tbody'),
    tr: createRenderer("markdown-table-row", 'tr'),
    th: createRenderer("markdown-table-header", 'th'),
    td: createRenderer("markdown-table-cell", 'td'),
    a: ({ href, children, ...props }: { href: string, children: React.ReactNode }) => {
      // Check if this is an external link that should open in a new tab
      const isExternalLink = href && (
        href.startsWith('http://') ||
        href.startsWith('https://') ||
        href.includes('docs.google.com') ||
        href.includes('drive.google.com') ||
        href.includes('salesforce.com') ||
        href.includes('lightning.force.com') ||
        href.endsWith('.pdf')
      );

      if (isExternalLink) {
        return (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="markdown-external-link"
            aria-label={`${children} (opens in new tab)`}
            {...props}
          >
            {children}
          </a>
        );
      }

      // For internal links, use default behavior
      return (
        <a href={href} className="markdown-internal-link" {...props}>
          {children}
        </a>
      );
    },
    img: ({ src, alt, title }: { src: string, alt: string, title: string }) => {
      const isThumbnail = src.includes('.thumbnail.jpg');

      // Ensure we have valid values for alt and title
      const safeAlt = alt || 'Image';
      const safeTitle = title || 'No title provided';

      // Log the image details for debugging
      // console.log("Rendering image:", { src, alt: safeAlt, title: safeTitle, isThumbnail });

      return (
        <img
          src={src}
          alt={safeAlt}
          title={safeTitle}
          onClick={() => {
            console.log("Image clicked in MarkdownMessage:", { src, alt: safeAlt, title: safeTitle });
            onImageClick(src, safeAlt, safeTitle);
          }}
          style={{
            cursor: 'pointer',
            borderRadius: '8px',
            width: isThumbnail ? 'auto' : '300px',
            height: isThumbnail ? 'auto' : '200px',
            objectFit: 'cover',
            display: 'block', // Ensure image is displayed as block
            margin: '10px 0', // Add some margin for spacing
          }}
          onError={(e) => {
            console.error("Image failed to load:", src);
            // Optionally set a fallback image or add a class for styling
            e.currentTarget.style.display = 'none';
          }}
        />
      );
    },
  };

  // Custom sanitization schema
  const sanitizeSchema = {
    ...defaultSchema,
    attributes: {
      ...defaultSchema.attributes,
      img: [...(defaultSchema.attributes?.img || []), 'style']
    },
    tagNames: [
      ...(defaultSchema.tagNames || []),
      'img'
    ]
  };

  return (
    <ReactMarkdown
      children={text}
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw, [rehypeSanitize, sanitizeSchema]]}
      components={renderers}
    />
  );
};

export default MarkdownMessage;
