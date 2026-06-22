import { Router, Request, Response } from "express";
import multer from "multer";
import FormData from "form-data";
import fs from "fs";
import axios from "axios";
import { asyncHandler } from "../../middleware/asyncHandler";
import { AgencyImport } from "../../models/AgencyImport";
import { env } from "../../config/env";

const router = Router();
const upload = multer({ storage: multer.memoryStorage() });

interface AgencyImportRequest extends Request {
  file?: Express.Multer.File;
  body: {
    agency_name?: string;
    format?: string;
  };
}

router.post(
  "/import-agency-form",
  upload.single("file"),
  asyncHandler(async (req: AgencyImportRequest, res: Response) => {
    const { agency_name, format } = req.body;

    if (!agency_name || !agency_name.trim()) {
      return res.status(400).json({ error: "agency_name is required" });
    }

    if (!req.file) {
      return res.status(400).json({ error: "No file provided" });
    }

    const supportedFormats = ["csv", "xlsx", "xls", "json"];
    const detectedFormat =
      format ||
      req.file.originalname.split(".").pop()?.toLowerCase() ||
      "";

    if (!supportedFormats.includes(detectedFormat)) {
      return res.status(400).json({
        error: `Unsupported format: ${detectedFormat}. Supported: csv, xlsx, xls, json`,
      });
    }

    try {
      const formData = new FormData();
      formData.append("file", req.file.buffer, {
        filename: req.file.originalname,
      });
      formData.append("agency_name", agency_name);

      const mlServiceUrl = env.ML_SERVICE_URL;
      const mlResponse = await axios.post(
        `${mlServiceUrl}/adapter/import`,
        formData,
        {
          headers: formData.getHeaders(),
          timeout: 60000,
        }
      );

      if (!mlResponse.data.success) {
        return res.status(400).json({
          error: mlResponse.data.error || "Import failed in ML service",
        });
      }

      const importDoc = new AgencyImport({
        agency: agency_name,
        records: mlResponse.data.records || [],
        mapping_metadata: mlResponse.data.mapping_metadata || {},
        import_count: mlResponse.data.records_imported || 0,
        unmapped_fields: mlResponse.data.unmapped_fields || [],
      });

      await importDoc.save();

      return res.status(200).json({
        success: true,
        agency: agency_name,
        records_imported: mlResponse.data.records_imported,
        mapping_confidence: mlResponse.data.mapping_confidence,
        unmapped_fields: mlResponse.data.unmapped_fields,
        sample_record: mlResponse.data.sample_record,
        db_import_id: importDoc._id,
      });
    } catch (error: any) {
      const errorMsg =
        error.response?.data?.detail ||
        error.message ||
        "Failed to import agency data";
      return res.status(error.response?.status || 500).json({
        error: errorMsg,
      });
    }
  })
);

export const adminRoutes = router;
