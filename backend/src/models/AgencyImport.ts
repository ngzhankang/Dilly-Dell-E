import mongoose from "mongoose";
import { z } from "zod";

export const UnifiedAgencyRecordSchema = z.object({
  name: z.string().optional(),
  dob: z.string().optional(),
  age: z.number().optional(),
  contact: z.string().optional(),
  emotion: z.enum(["happy", "neutral", "worried", "confused"]).optional(),
  problem_classes: z.array(z.string()).optional(),
  special_case: z.string().optional(),
});

export type UnifiedAgencyRecord = z.infer<typeof UnifiedAgencyRecordSchema>;

interface AgencyImportDoc {
  agency: string;
  agency_patient_id?: string;
  our_patient_id?: string;
  records: UnifiedAgencyRecord[];
  mapping_metadata: {
    source_to_target: Record<string, string | null>;
    confidence: number;
    unmapped: string[];
  };
  import_timestamp: Date;
  import_count: number;
  unmapped_fields: string[];
}

const agencyImportSchema = new mongoose.Schema<AgencyImportDoc>(
  {
    agency: { type: String, required: true },
    agency_patient_id: { type: String },
    our_patient_id: { type: String },
    records: [
      {
        name: String,
        dob: String,
        age: Number,
        contact: String,
        emotion: { type: String, enum: ["happy", "neutral", "worried", "confused"] },
        problem_classes: [String],
        special_case: String,
      },
    ],
    mapping_metadata: {
      source_to_target: mongoose.Schema.Types.Mixed,
      confidence: Number,
      unmapped: [String],
    },
    import_timestamp: { type: Date, default: () => new Date() },
    import_count: { type: Number, required: true },
    unmapped_fields: [String],
  },
  { timestamps: true }
);

export const AgencyImport = mongoose.model<AgencyImportDoc>(
  "AgencyImport",
  agencyImportSchema
);
