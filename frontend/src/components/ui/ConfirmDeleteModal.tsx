import React from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmDeleteModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    message: string;
    itemName: string;
}

export const ConfirmDeleteModal: React.FC<ConfirmDeleteModalProps> = ({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    itemName,
}) => {
    React.useEffect(() => {
        const handleEsc = (event: KeyboardEvent) => {
            if (event.key === 'Escape') onClose();
        };
        if (isOpen) {
            window.addEventListener('keydown', handleEsc);
        }
        return () => {
            window.removeEventListener('keydown', handleEsc);
        };
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/40 backdrop-blur-sm animate-fade-in"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-scale-in border border-gray-100">
                <div className="p-6">
                    <div className="flex items-start justify-between">
                        <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center shrink-0">
                            <AlertTriangle className="text-red-500" size={24} />
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1 rounded-full text-gray-400 hover:text-gray-900 hover:bg-gray-100 transition-colors"
                        >
                            <X size={20} />
                        </button>
                    </div>

                    <div className="mt-5">
                        <h3 className="text-lg font-bold text-gray-900 leading-6">
                            {title}
                        </h3>
                        <p className="mt-3 text-[14px] text-gray-500 leading-relaxed">
                            {message} <span className="font-semibold text-gray-900 italic">"{itemName}"</span>?
                            <br />
                            <span className="text-red-600 font-medium mt-2 block">This action is permanent and cannot be undone.</span>
                        </p>
                    </div>
                </div>

                <div className="bg-gray-50 px-6 py-4 flex flex-col sm:flex-row-reverse gap-3">
                    <button
                        type="button"
                        onClick={() => {
                            onConfirm();
                            onClose();
                        }}
                        className="w-full sm:w-auto px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white rounded-xl text-[14px] font-bold shadow-sm shadow-red-200 transition-all active:scale-95"
                    >
                        Delete Forever
                    </button>
                    <button
                        type="button"
                        onClick={onClose}
                        className="w-full sm:w-auto px-6 py-2.5 bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 rounded-xl text-[14px] font-semibold transition-all"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </div>
    );
};
