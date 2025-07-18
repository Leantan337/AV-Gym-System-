import axios from 'axios';

// Determine API URL based on environment
const getApiBaseUrl = () => {
  const baseUrl = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
  return baseUrl.endsWith('/api') ? baseUrl : `${baseUrl}/api`;
};

// Create axios instance with base URL and auth headers
const api = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
import {
  Invoice,
  InvoiceTemplate,
  CreateInvoiceData,
  UpdateInvoiceData,
  InvoiceFilters,
  InvoiceListResponse,
} from '../types/invoice';

export const invoiceApi = {
  // Invoice Templates
  getTemplates: async () => {
    const response = await api.get<InvoiceTemplate[]>('/invoice-templates/');
    return response.data;
  },

  getTemplate: async (id: string) => {
    const response = await api.get<InvoiceTemplate>(`/invoice-templates/${id}/`);
    return response.data;
  },

  createTemplate: async (data: Omit<InvoiceTemplate, 'id' | 'createdAt' | 'updatedAt'>) => {
    const response = await api.post<InvoiceTemplate>('/invoice-templates/', data);
    return response.data;
  },

  updateTemplate: async (id: string, data: Partial<InvoiceTemplate>) => {
    const response = await api.patch<InvoiceTemplate>(`/invoice-templates/${id}/`, data);
    return response.data;
  },

  deleteTemplate: async (id: string) => {
    await api.delete(`/invoice-templates/${id}/`);
  },

  // Invoices
  getInvoices: async (filters: InvoiceFilters = {}): Promise<InvoiceListResponse> => {
    const params = new URLSearchParams();
    if (filters.search) params.append('q', filters.search);
    if (filters.status && filters.status !== 'all') params.append('status', filters.status);
    if (filters.dateRange) params.append('dateRange', filters.dateRange);
    if (filters.startDate) params.append('startDate', filters.startDate);
    if (filters.endDate) params.append('endDate', filters.endDate);
    if (filters.page !== undefined) params.append('page', filters.page.toString());
    if (filters.perPage) params.append('perPage', filters.perPage.toString());

    const response = await api.get<InvoiceListResponse>(`/invoices/?${params.toString()}`);
    return response.data;
  },

  getInvoice: async (id: string) => {
    const response = await api.get<Invoice>(`/invoices/${id}/`);
    return response.data;
  },

  // Alias for getInvoice for backward compatibility
  getInvoiceById: async (id: string) => {
    return invoiceApi.getInvoice(id);
  },
  
  // Download invoice as PDF
  downloadInvoicePdf: async (id: string) => {
    const response = await api.get(`/invoices/${id}/pdf/`, {
      responseType: 'blob',
    });
    return response.data;
  },

  createInvoice: async (data: CreateInvoiceData) => {
    const response = await api.post<Invoice>('/invoices/', data);
    return response.data;
  },

  updateInvoice: async (id: string, data: UpdateInvoiceData) => {
    const response = await api.patch<Invoice>(`/invoices/${id}/`, data);
    return response.data;
  },

  deleteInvoice: async (id: string) => {
    await api.delete(`/invoices/${id}/`);
  },

  // Bulk Operations
  bulkUpdateStatus: async (invoiceIds: string[], status: Invoice['status']) => {
    const response = await api.post<{ updated: number }>('/invoices/bulk-update/', {
      invoiceIds,
      status,
    });
    return response.data;
  },

  generatePdf: async (id: string) => {
    const response = await api.get(`/invoices/${id}/pdf/`, {
      responseType: 'blob',
    });
    return response.data;
  },

  bulkGeneratePdf: async (invoiceIds: string[]) => {
    const response = await api.post('/invoices/bulk-pdf/', { invoiceIds }, {
      responseType: 'blob',
    });
    return response.data;
  },

  // Email invoice
  sendInvoiceEmail: async (invoiceId: string, email?: string) => {
    const response = await api.post<{ success: boolean; message: string }>(
      `/invoices/${invoiceId}/send/`,
      { recipientEmail: email }
    );
    return response.data;
  },

  // Mark invoice as paid
  markInvoiceAsPaid: async (invoiceId: string) => {
    const response = await api.patch<Invoice>(`/invoices/${invoiceId}/`, {
      status: 'paid',
      paidAt: new Date().toISOString(),
    });
    return response.data;
  },

  // Get invoice statistics
  getInvoiceStats: async (dateRange?: InvoiceFilters['dateRange']) => {
    const params = new URLSearchParams();
    if (dateRange) params.append('dateRange', dateRange);

    const response = await api.get<{
      totalCount: number;
      totalAmount: number;
      paidAmount: number;
      pendingAmount: number;
      overdueAmount: number;
      byStatus: Record<Invoice['status'], number>;
      byMonth: Array<{ month: string; amount: number; count: number }>;
    }>(`/invoices/stats/?${params.toString()}`);
    return response.data;
  },

  // Get invoice analytics
  getInvoiceAnalytics: async (startDate: string, endDate: string, period: string) => {
    const response = await api.get<{
      labels: string[];
      datasets: Array<{
        label: string;
        data: number[];
        backgroundColor: string;
      }>;
    }>('/invoices/analytics/', {
      params: { startDate, endDate, period }
    });
    return response.data;
  },

  // Get top members by invoice value
  getTopMembers: async (startDate: string, endDate: string, limit = 5) => {
    const response = await api.get<Array<{
      memberId: string;
      memberName: string;
      totalAmount: number;
      invoiceCount: number;
    }>>('/invoices/top-members/', {
      params: { startDate, endDate, limit }
    });
    return response.data;
  },
};
