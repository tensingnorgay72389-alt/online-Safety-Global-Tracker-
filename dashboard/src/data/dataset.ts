import marketsFile from '../../data/markets.json'
import regulationsFile from '../../data/regulations.json'
import newsFile from '../../data/news_items.json'
import jurisdictionsFile from '../../data/jurisdictions.json'
import serviceTypesFile from '../../data/service_types.json'
import registerMetaFile from '../../data/register_meta.json'
import type { Jurisdiction, Market, NewsItem, Regulation, ServiceType } from '../types'

export const baselineMarkets = marketsFile.markets as Market[]
export const regulations = regulationsFile.regulations as Regulation[]
export const newsItems = newsFile.news_items as NewsItem[]
export const jurisdictions = jurisdictionsFile.jurisdictions as Jurisdiction[]
export const serviceTypes = serviceTypesFile.service_types as ServiceType[]
export const registerMeta = registerMetaFile
export const lastUpdated = regulationsFile.last_updated || marketsFile.last_updated

export const verifiedRegisterCounts = regulationsFile.verified_register.counts
