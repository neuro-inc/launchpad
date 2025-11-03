import { z } from 'zod';

/**
 * Zod validation schemas for Admin forms
 */

// Helper for optional string fields that can be empty
const optionalString = z.string();

/**
 * Schema for ImportAppRequest
 * Note: tags field is kept as string in the form and converted to array on submit
 */
export const importAppSchema = z.object({
  appId: z
    .string()
    .min(1, 'App ID is required')
    .uuid('App ID must be a valid UUID'),
  name: optionalString,
  verboseName: optionalString,
  descriptionShort: optionalString,
  descriptionLong: optionalString,
  logo: z
    .string()
    .refine(
      (val) => !val || val.startsWith('http://') || val.startsWith('https://'),
      'Logo must be a valid URL',
    ),
  tags: z.string(), // Kept as string, will be split into array on submit
  isInternal: z.boolean(),
});

export type ImportAppFormData = z.infer<typeof importAppSchema>;

/**
 * Schema for ImportTemplateRequest
 * Note: tags and input fields have special handling
 */
export const importTemplateSchema = z.object({
  templateName: z.string().min(1, 'Template name is required'),
  templateVersion: z.string().min(1, 'Template version is required'),
  name: optionalString,
  verboseName: optionalString,
  descriptionShort: optionalString,
  descriptionLong: optionalString,
  logo: z
    .string()
    .refine(
      (val) => !val || val.startsWith('http://') || val.startsWith('https://'),
      'Logo must be a valid URL',
    ),
  tags: z.string(), // Kept as string, will be split into array on submit
  isInternal: z.boolean(),
  isShared: z.boolean(),
  input: z.string(), // Kept as string (JSON), will be parsed on submit
});

export type ImportTemplateFormData = z.infer<typeof importTemplateSchema>;
