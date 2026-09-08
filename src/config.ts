import { Search, Fingerprint, AlertTriangle, Share2 } from 'lucide-react';
import type { InvestigationTypeConfig, InvestigationTypeKey } from './types';
export const INVESTIGATION_TYPES: Record<InvestigationTypeKey, InvestigationTypeConfig> = {
 'verify-media': {label:'Verify Media',icon:Search,prompt:'What do you already know about this media?',question:'Describe the media and why it\'s suspicious.',placeholder:'e.g. "A video circulating claiming to show a factory fire in Ludhiana last night."'},
 'media-dna': {label:'Media DNA Search',icon:Fingerprint,prompt:'Let\'s search the evidence network.',question:'Describe the media you want to search for.',placeholder:'e.g. "A protest photo that looks similar to one we processed last year."'},
 'verify-claim': {label:'Verify a Claim',icon:AlertTriangle,prompt:'Let\'s start with what you know.',question:'What is being claimed?',placeholder:'e.g. "This image shows an incident that occurred in Chandigarh today."'},
 'trace-propagation': {label:'Trace Propagation',icon:Share2,prompt:'Let\'s trace where this came from.',question:'What content do you want to trace?',placeholder:'e.g. "A clip that suddenly appeared across five WhatsApp groups this morning."'}
};
export const INVESTIGATION_TYPE_LABEL:Record<InvestigationTypeKey,string>={ 'verify-media':'Verify Media','media-dna':'Media DNA Search','verify-claim':'Verify Claim','trace-propagation':'Propagation Trace'};
export const DEFAULT_NEW_CASE_PRIORITY='HIGH' as const;
