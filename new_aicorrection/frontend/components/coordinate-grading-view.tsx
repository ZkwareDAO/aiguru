"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { MapPin, X, Eye, BookOpen, Target } from 'lucide-react';

interface Coordinates {
  x: number;
  y: number;
  w: number;
  h: number;
}

interface ErrorDetails {
  type: string;
  description: string;
  correct_answer: string;
  severity: string;
}

interface PopupContent {
  title: string;
  description: string;
  correct_solution: string;
  knowledge_links: string[];
}

interface CoordinateAnnotation {
  annotation_id: string;
  coordinates: Coordinates;
  error_details: ErrorDetails;
  knowledge_points: string[];
  popup_content: PopupContent;
}

interface CoordinateGradingViewProps {
  originalImageUrl: string;
  annotations: CoordinateAnnotation[];
  gradingSummary: {
    score: number;
    max_score: number;
    percentage: number;
    feedback: string;
    strengths: string[];
    suggestions: string[];
  };
  knowledgePointSummary: {
    total_points: number;
    points: string[];
    mastery_analysis: any;
  };
}

export default function CoordinateGradingView({
  originalImageUrl,
  annotations,
  gradingSummary,
  knowledgePointSummary
}: CoordinateGradingViewProps) {
  const [selectedAnnotation, setSelectedAnnotation] = useState<CoordinateAnnotation | null>(null);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageScale, setImageScale] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [viewMode, setViewMode] = useState<'original' | 'annotated'>('annotated');
  
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load and display image with annotations
  useEffect(() => {
    if (imageLoaded && canvasRef.current && imageRef.current) {
      drawImageWithAnnotations();
    }
  }, [imageLoaded, imageScale, panOffset, viewMode, annotations]);

  const drawImageWithAnnotations = () => {
    const canvas = canvasRef.current;
    const image = imageRef.current;
    
    if (!canvas || !image) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw image
    const scaledWidth = image.naturalWidth * imageScale;
    const scaledHeight = image.naturalHeight * imageScale;
    
    ctx.drawImage(
      image,
      panOffset.x,
      panOffset.y,
      scaledWidth,
      scaledHeight
    );
    
    // Draw annotations if in annotated mode
    if (viewMode === 'annotated') {
      annotations.forEach((annotation, index) => {
        const coords = annotation.coordinates;
        const x = coords.x * imageScale + panOffset.x;
        const y = coords.y * imageScale + panOffset.y;
        const w = coords.w * imageScale;
        const h = coords.h * imageScale;
        
        // Draw error rectangle
        ctx.strokeStyle = getSeverityColor(annotation.error_details.severity);
        ctx.lineWidth = 3;
        ctx.strokeRect(x, y, w, h);
        
        // Draw error point
        const centerX = x + w / 2;
        const centerY = y + h / 2;
        
        ctx.fillStyle = getSeverityColor(annotation.error_details.severity);
        ctx.beginPath();
        ctx.arc(centerX, centerY, 8, 0, 2 * Math.PI);
        ctx.fill();
        
        // Draw annotation number
        ctx.fillStyle = 'white';
        ctx.font = 'bold 12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText((index + 1).toString(), centerX, centerY + 4);
      });
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return '#ef4444'; // red
      case 'medium': return '#f97316'; // orange  
      case 'low': return '#eab308'; // yellow
      default: return '#ef4444';
    }
  };

  const handleCanvasClick = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;
    
    // Check if click is on any annotation
    for (const annotation of annotations) {
      const coords = annotation.coordinates;
      const x = coords.x * imageScale + panOffset.x;
      const y = coords.y * imageScale + panOffset.y;
      const w = coords.w * imageScale;
      const h = coords.h * imageScale;
      
      if (clickX >= x && clickX <= x + w && clickY >= y && clickY <= y + h) {
        setSelectedAnnotation(annotation);
        break;
      }
    }
  };

  const handleZoomIn = () => {
    setImageScale(prev => Math.min(prev * 1.2, 3));
  };

  const handleZoomOut = () => {
    setImageScale(prev => Math.max(prev / 1.2, 0.5));
  };

  const handleResetView = () => {
    setImageScale(1);
    setPanOffset({ x: 0, y: 0 });
  };

  const handleMouseDown = (event: React.MouseEvent) => {
    setIsPanning(true);
    setPanStart({ x: event.clientX - panOffset.x, y: event.clientY - panOffset.y });
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    if (!isPanning) return;
    setPanOffset({
      x: event.clientX - panStart.x,
      y: event.clientY - panStart.y
    });
  };

  const handleMouseUp = () => {
    setIsPanning(false);
  };

  return (
    <div className=\"space-y-6\">
      {/* Header Controls */}
      <Card>
        <CardHeader>
          <CardTitle className=\"flex items-center justify-between\">
            <span className=\"flex items-center gap-2\">
              <Target className=\"w-5 h-5\" />
              坐标标注批改结果
            </span>
            <div className=\"flex items-center gap-2\">
              <Button
                variant={viewMode === 'original' ? 'default' : 'outline'}
                size=\"sm\"
                onClick={() => setViewMode('original')}
              >
                <Eye className=\"w-4 h-4 mr-1\" />
                原图
              </Button>
              <Button
                variant={viewMode === 'annotated' ? 'default' : 'outline'}
                size=\"sm\"
                onClick={() => setViewMode('annotated')}
              >
                <MapPin className=\"w-4 h-4 mr-1\" />
                标注图
              </Button>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className=\"flex items-center justify-between mb-4\">
            <div className=\"flex items-center gap-4\">
              <div className=\"text-2xl font-bold text-primary\">
                {gradingSummary.score}/{gradingSummary.max_score}
              </div>
              <div className=\"text-lg text-muted-foreground\">
                {gradingSummary.percentage.toFixed(1)}%
              </div>
              <Badge variant={gradingSummary.percentage >= 80 ? 'default' : gradingSummary.percentage >= 60 ? 'secondary' : 'destructive'}>
                {gradingSummary.percentage >= 80 ? '优秀' : gradingSummary.percentage >= 60 ? '良好' : '需要改进'}
              </Badge>
            </div>
            <div className=\"flex items-center gap-2\">
              <Button size=\"sm\" variant=\"outline\" onClick={handleZoomOut}>
                -
              </Button>
              <span className=\"text-sm font-mono w-12 text-center\">
                {Math.round(imageScale * 100)}%
              </span>
              <Button size=\"sm\" variant=\"outline\" onClick={handleZoomIn}>
                +
              </Button>
              <Button size=\"sm\" variant=\"outline\" onClick={handleResetView}>
                重置
              </Button>
            </div>
          </div>
          
          {/* Image Canvas */}
          <div 
            ref={containerRef}
            className=\"relative border rounded-lg overflow-hidden bg-gray-50\"
            style={{ height: '500px', cursor: isPanning ? 'grabbing' : 'grab' }}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            <img
              ref={imageRef}
              src={originalImageUrl}
              alt=\"批改原图\"
              className=\"hidden\"
              onLoad={() => {
                setImageLoaded(true);
                const img = imageRef.current;
                const canvas = canvasRef.current;
                if (img && canvas) {
                  canvas.width = img.naturalWidth;
                  canvas.height = img.naturalHeight;
                }
              }}
            />
            <canvas
              ref={canvasRef}
              className=\"absolute inset-0 w-full h-full object-contain\"
              onClick={handleCanvasClick}
              style={{ cursor: 'crosshair' }}
            />
            
            {/* Annotation Legend */}
            {viewMode === 'annotated' && (
              <div className=\"absolute top-4 left-4 bg-white/90 backdrop-blur rounded-lg p-3 space-y-2\">
                <div className=\"text-sm font-medium\">错误标注</div>
                {annotations.map((annotation, index) => (
                  <div key={annotation.annotation_id} className=\"flex items-center gap-2 text-xs\">
                    <div 
                      className=\"w-3 h-3 rounded-full\"
                      style={{ backgroundColor: getSeverityColor(annotation.error_details.severity) }}
                    />
                    <span>{index + 1}. {annotation.error_details.type.replace('_', ' ')}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Instructions */}
          <div className=\"mt-4 text-sm text-muted-foreground text-center\">
            {viewMode === 'annotated' ? (
              <span>🖱️ 点击红色标记查看详细错误信息 | 拖拽移动 | 使用缩放控制查看细节</span>
            ) : (
              <span>📷 查看原始作业图片 | 拖拽移动 | 使用缩放控制查看细节</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Grading Summary */}
      <div className=\"grid grid-cols-1 md:grid-cols-2 gap-6\">
        {/* Feedback */}
        <Card>
          <CardHeader>
            <CardTitle>批改反馈</CardTitle>
          </CardHeader>
          <CardContent className=\"space-y-4\">
            <p className=\"text-sm leading-relaxed\">{gradingSummary.feedback}</p>
            
            {gradingSummary.strengths.length > 0 && (
              <div>
                <h4 className=\"font-medium text-green-700 mb-2\">优点</h4>
                <ul className=\"text-sm space-y-1\">
                  {gradingSummary.strengths.map((strength, index) => (
                    <li key={index} className=\"flex items-start gap-2\">
                      <span className=\"text-green-500 mt-1\">✓</span>
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {gradingSummary.suggestions.length > 0 && (
              <div>
                <h4 className=\"font-medium text-amber-700 mb-2\">改进建议</h4>
                <ul className=\"text-sm space-y-1\">
                  {gradingSummary.suggestions.map((suggestion, index) => (
                    <li key={index} className=\"flex items-start gap-2\">
                      <span className=\"text-amber-500 mt-1\">💡</span>
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Knowledge Points */}
        <Card>
          <CardHeader>
            <CardTitle className=\"flex items-center gap-2\">
              <BookOpen className=\"w-5 h-5\" />
              知识点分析
            </CardTitle>
          </CardHeader>
          <CardContent className=\"space-y-4\">
            <div className=\"flex items-center gap-4\">
              <div className=\"text-sm\">
                <span className=\"font-medium\">涉及知识点：</span>
                <span className=\"ml-1\">{knowledgePointSummary.total_points}个</span>
              </div>
            </div>
            
            <div className=\"flex flex-wrap gap-2\">
              {knowledgePointSummary.points.map((point, index) => (
                <Badge key={index} variant=\"outline\">
                  {point}
                </Badge>
              ))}
            </div>
            
            {knowledgePointSummary.mastery_analysis?.weak_areas?.length > 0 && (
              <div>
                <h4 className=\"font-medium text-red-700 mb-2\">薄弱环节</h4>
                <div className=\"space-y-2\">
                  {knowledgePointSummary.mastery_analysis.weak_areas.map((area: any, index: number) => (
                    <div key={index} className=\"flex items-center justify-between\">
                      <span className=\"text-sm\">{area.knowledge_point}</span>
                      <Badge variant={area.severity === 'high' ? 'destructive' : area.severity === 'medium' ? 'secondary' : 'outline'}>
                        {area.error_count}处错误
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {knowledgePointSummary.mastery_analysis?.recommendations?.length > 0 && (
              <div>
                <h4 className=\"font-medium text-blue-700 mb-2\">学习建议</h4>
                <ul className=\"text-sm space-y-1\">
                  {knowledgePointSummary.mastery_analysis.recommendations.map((rec: string, index: number) => (
                    <li key={index} className=\"flex items-start gap-2\">
                      <span className=\"text-blue-500 mt-1\">📚</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Error Detail Dialog */}
      <Dialog open={!!selectedAnnotation} onOpenChange={() => setSelectedAnnotation(null)}>
        <DialogContent className=\"max-w-md\">
          {selectedAnnotation && (
            <>
              <DialogHeader>
                <DialogTitle className=\"flex items-center gap-2\">
                  <div 
                    className=\"w-4 h-4 rounded-full\"
                    style={{ backgroundColor: getSeverityColor(selectedAnnotation.error_details.severity) }}
                  />
                  {selectedAnnotation.popup_content.title}
                </DialogTitle>
              </DialogHeader>
              <div className=\"space-y-4\">
                <div>
                  <h4 className=\"font-medium mb-2\">错误说明</h4>
                  <p className=\"text-sm text-muted-foreground\">
                    {selectedAnnotation.popup_content.description}
                  </p>
                </div>
                
                {selectedAnnotation.popup_content.correct_solution && (
                  <div>
                    <h4 className=\"font-medium mb-2\">正确解法</h4>
                    <p className=\"text-sm text-muted-foreground bg-green-50 p-3 rounded\">
                      {selectedAnnotation.popup_content.correct_solution}
                    </p>
                  </div>
                )}
                
                {selectedAnnotation.knowledge_points.length > 0 && (
                  <div>
                    <h4 className=\"font-medium mb-2\">相关知识点</h4>
                    <div className=\"flex flex-wrap gap-2\">
                      {selectedAnnotation.knowledge_points.map((point, index) => (
                        <Badge key={index} variant=\"outline\">
                          {point}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className=\"flex justify-end gap-2\">
                  <Button variant=\"outline\" onClick={() => setSelectedAnnotation(null)}>
                    关闭
                  </Button>
                  <Button>
                    查看相关练习
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}