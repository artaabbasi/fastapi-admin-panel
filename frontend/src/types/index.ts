export interface FieldSchema {
  name: string;
  field_type:
    | "string"
    | "text"
    | "integer"
    | "float"
    | "boolean"
    | "date"
    | "datetime"
    | "time"
    | "json"
    | "uuid"
    | "enum"
    | "binary";
  primary_key: boolean;
  nullable: boolean;
  default: unknown;
  foreign_key: string | null;
  choices: string[];
  max_length: number | null;
}

export interface ModelSchema {
  name: string;
  table_name: string;
  pk_field: string;
  fields: FieldSchema[];
}

export interface ListResponse<T = Record<string, unknown>> {
  total: number;
  skip: number;
  limit: number;
  data: T[];
}

export interface ListParams {
  skip?: number;
  limit?: number;
  search?: string;
  search_field?: string;
  order_by?: string;
  order_dir?: "asc" | "desc";
}
